# ProofyX VerifyOps + Interview Portal

One project, one folder (`D:\HR Bot`). It contains:

1. **Verification Gate**: an API that scores photos and PDFs and returns **PASS / REVIEW / BLOCK**.
2. **FieldProof**: rule-based fraud checks (duplicate photos, EXIF/GPS/time, hidden text in PDFs).
3. **EvidenceVault**: signed, tamper-evident PDF certificates for each check.
4. **Review queue**: a web page where a person confirms fraud or marks authentic. Each click becomes training data.
5. **Interview portal**: HR login, schedule a meeting + link, candidate joins by web with camera, mic and consented screen sharing.
6. **Training code**: three detector models (face, scene, document) trained in Google Colab, giving `.pth` files.

---

## 1. Where things stand (read this first)

| Item | Status | Notes |
|---|---|---|
| Gate API, FieldProof, EvidenceVault, review queue | **Built, 14 automated tests pass** | Works without any ML model (rule checks only) |
| Interview portal | **Built, tested through the API/WebSocket** | **Not yet tried by a person in two real browsers.** Do this before relying on it |
| **Face model** | Quick-size run only | Best: `trained\face_10ep_600img.pth` (val AUC 0.98 on only 400 images, 600 training images). **Needs the full run** |
| **Scene model** | Quick-size run only | AUC 0.90 on 600 training images. **Needs the full run** |
| **Document model** | Pipeline proven, 1-epoch test only | AUC 0.70. **Needs the full run** |
| ONNX files in `models/` | **None yet** | The Gate only uses ML once `models\face.onnx`, `scene.onnx`, `document.onnx` exist |

> The scores above come from the **same dataset** the models trained on. They overstate real-world performance. Section 7 explains how to test honestly.

---

## 2. Folder map

```
D:\HR Bot
  app\                      the server (FastAPI)
    main.py                 Gate API + review queue + evidence endpoints
    gate\                   model loading (ONNX), verdict rules
    fieldproof\             duplicate photos, EXIF/GPS/time, PDF audit
    evidence\               certificates (Ed25519 signed, hash-chained)
    meet\                   login, HR scheduling, meeting room (WebRTC)
    review\                 review-queue page
  training\                 model code + data download + training loop
  colab\
    train_face.py           RUN 1  (face model)       <- upload to Colab
    train_scene.py          RUN 2  (scene model)      <- upload to Colab
    train_document.py       RUN 3  (document model)   <- upload to Colab
    train_one.py            all-in-one version (any task via --task)
    ProofyX_train_colab.ipynb, training.zip   older notebook route (optional)
  scripts\
    create_user.py          create an HR login
    export_onnx.py          .pth  ->  ONNX (checks it matches)
    eval_folder.py          INDEPENDENT test of a model on your own images
  models\                   put face.onnx / scene.onnx / document.onnx here
  trained\                  keep your good .pth files here (backup)
  data\                     database, certificates, signing key (back this up; never share signing_key.pem)
  tests\                    automated tests
  requirements*.txt, setup_venv.ps1, Dockerfile, docker-compose.yml
```

---

## 3. Setup (virtual environment)

```powershell
cd "D:\HR Bot"
powershell -ExecutionPolicy Bypass -File setup_venv.ps1     # one time; creates .venv (a few GB, includes PyTorch)
.\.venv\Scripts\Activate.ps1
python -m pytest -q                                         # expect: 14 passed
```
- Serving only (small install): `pip install -r requirements.txt`.
- Training/export tools: `requirements-train.txt` (already included by `requirements-dev.txt`).
- The venv already exists in this folder. Just activate it.

---

## 4. Run the server and the interview portal

```powershell
python scripts\create_user.py hr@yourcompany.com "Your Name" "a-long-password-10+"
$env:VERIFYOPS_PUBLIC_URL = "http://localhost:8000"      # the address candidates will open
uvicorn app.main:app --port 8000
```
Open `http://localhost:8000`.

**HR:** sign in, then fill title, date/time, candidate name and email, and press *Create meeting & link*. A new candidate gets a one-time temporary password shown once on screen. If email (SMTP) is not configured, copy the link and password and send them yourself.

**Candidate:** signs in (sets their own password on first login), opens the link, reads what will be shared, ticks the consent box, and presses *Agree & join*. The browser then asks for camera, microphone and screen. They must choose **Entire screen**. HR sees camera and screen live. A red banner reminds the candidate while their screen is shared. If they stop sharing, HR is told.

**Rules you can't change (browser behaviour):**
- Camera and screen capture work only on **HTTPS or `localhost`**. A plain `http://192.168.x.x` link will not work. For real candidates use HTTPS (a reverse proxy or a tunnel).
- The website can never silently access a machine. The browser always shows its own picker.
- Candidates on other networks usually need a **TURN server** (see env vars).
- Join window: 15 minutes before start to 60 minutes after the end.

---

## 5. Verification API

```powershell
curl -H "X-API-Key: dev-key" -F file=@photo.jpg -F entity_id=VEH-123 -F dealer_id=D7 `
     -F activation_time=2026-11-20T10:05:00Z -F activation_lat=13.08 -F activation_lon=80.27 `
     http://localhost:8000/api/v1/verify
```
Interactive docs: `http://localhost:8000/docs`. **Change the API key** (`VERIFYOPS_API_KEYS`); `dev-key` is for local use only.

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/verify` | Upload an image or PDF, get the verdict. Optional `image_type=auto/photo/face/document` |
| `GET /api/v1/verifications/{id}` | Fetch a past result |
| `GET /api/v1/verifications/{id}/heatmap` | Heatmap image (ELA overlay now; Grad-CAM later) |
| `GET /api/v1/verifications/{id}/certificate` | Signed PDF (`?format=json` for the machine copy) |
| `GET /api/v1/evidence/verify-chain` | Re-checks every certificate's signature and chain |
| `GET /review` | Review queue page (enter the API key) |
| `GET /api/v1/review/export-labels` | Human labels for retraining |
| `GET /api/v1/stats` | Counts and escalation rate |
| `GET /health` | Which ML models are loaded |

**How the verdict works:** trust score starts at 100; the model score, ELA hint and each flag subtract points. Hard blocks: duplicate photo, hidden PDF text, invisible Unicode characters, text aimed at an AI screener. PASS needs score ≥ 70 and no high-severity flag; BLOCK below 30. With no ML model loaded, confidence is capped and says so.

**Limits:** EXIF can be faked, so EXIF flags raise review risk but never prove a photo is real. The certificate records a chain of custody; have a lawyer review its wording before calling it "compliant" with Indian evidence law.

---

## 6. Training the three models in Google Colab

Three models, trained **one per laptop, in this order**:

| Run | Script | Model | Data (Hugging Face) | Saves |
|---|---|---|---|---|
| **1** | `colab\train_face.py` | EfficientNet-B4 @380 | `pujanpaudel/deepfake_face_classification` (val.zip, test.zip, train.rar) | `face.pth` |
| **2** | `colab\train_scene.py` | CLIP ViT-B/16 + linear head | `TheKernel01/Tiny-GenImage`, equal share per generator | `scene.pth` |
| **3** | `colab\train_document.py` | ConvNeXt-Tiny @384 | Real invoices/receipts (3 sets) + synthetic tampering | `document.pth` |

### Steps for each run (replace `face` with `scene` or `document`)
1. Open Colab, then **Runtime → Change runtime type → T4 GPU**.
2. **Upload the script:** folder icon → upload icon → pick `D:\HR Bot\colab\train_face.py`. (Re-upload after every runtime restart; restarts wipe `/content`.)
3. **Cell A, mount Drive (once per session):**
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   ```
   "Drive already mounted" is normal. Ignore it.
4. **Cell B, quick test (a few minutes, saves `face_quick.pth`):**
   ```python
   !python -u /content/train_face.py --quick
   ```
5. If it runs without errors, **Cell C, the real run:**
   ```python
   !python -u /content/train_face.py --full
   ```
6. Keep the tab open. If Colab disconnects, run Cell A then Cell C again; it resumes from the last finished epoch.
7. When it finishes it saves to `MyDrive/proofyx/face.pth` and downloads to your computer.

**What a healthy log looks like:** `task=... train=... val=...`, then one `epoch N: ... val AUC ...` line per epoch, AUC rising; `saved best -> ...`. A quick test is only a pipeline check; its score doesn't matter much. For the scene run you should also see `saved per source: {...}` listing **every** generator (about equal counts).

**Rough time (not measured; depends on Colab):** face = several hours (3.9 GB download + 10 epochs at 380 px), scene = a couple of hours, document = under about two hours.

**Why the three models exist:** `face` catches face swaps and deepfaked portraits; `scene` catches AI-generated or edited photos (installation photos, vehicles); `document` catches tampered invoices/IDs. The Gate picks which apply (`image_type=auto` runs `scene` always and `face` only if a face is found).

**Data licences:** Tiny-GenImage is non-commercial (CC BY-NC-SA) and the face set is CC BY-NC 4.0. Fine for research and demos. **Get legal advice before selling a product built on these weights**, and plan to fine-tune on data you own (APM photos, consented samples; the review queue creates exactly that).

---

## 7. After training: what to do (checklist)

Do this **for each model** as its `.pth` arrives (usually in `C:\Users\samoh\Downloads\`).

1. **Copy it somewhere safe:** `D:\HR Bot\trained\face_full.pth` (a bad run can overwrite the Drive copy).
2. **Check the file is what you think:**
   ```powershell
   python -c "import torch;c=torch.load(r'D:\HR Bot\trained\face_full.pth',map_location='cpu',weights_only=True);print(c['task'],c['arch'],c['metrics'])"
   ```
   `task` must match (`face`/`scene`/`document`).
3. **Export to ONNX** (it also checks the ONNX output matches PyTorch):
   ```powershell
   python scripts\export_onnx.py "D:\HR Bot\trained\face_full.pth" --out data\candidate_models
   ```
4. **Independent test (the step that matters).** Make a folder of **images the model never saw, from a different source**, e.g. `D:\test\face\real\*.jpg` and `D:\test\face\fake\*.jpg`. Then:
   ```powershell
   python scripts\eval_folder.py --task face --data D:\test\face --model_dir data\candidate_models
   ```
   - AUC below 0.70 on the new source: **not ready.** Train more or on more varied data.
   - 0.70 to 0.85: usable only with human review (that is what REVIEW is for).
   - Above 0.85: promising. Keep checking on real APM data.
5. **Install it** only if it passes: copy the `.onnx` and `.json` files from `data\candidate_models` into `models\`.
6. **Restart the server** and confirm `http://localhost:8000/health` lists the model, for example `"models": ["document","face","scene"]`.
7. **Try the API** with a few real and fake files; read the verdict and the `analysis.model_scores` field.
8. Repeat for the other two models.

### After all three models are installed
1. **Run a pilot in "shadow mode"** (about 30 days): the system scores everything but humans decide. Use `/review` to confirm fraud or mark authentic.
2. **Collect labels:** `GET /api/v1/review/export-labels`. After roughly 500 to 1,000 labels per class, **retrain/fine-tune on APM's own images**. Always compare against the current model on a held-out set before replacing it.
3. **Tune thresholds** (`VERIFYOPS_PASS_AT`, `VERIFYOPS_BLOCK_BELOW`) so that only about 2 to 5% of items go to REVIEW/BLOCK.
4. **Deploy for the demo:** `docker compose up --build` (copy `.env.example` to `.env`, set a strong API key; put the `.onnx` files in `models\`). Runs fully offline except webhooks you allow-list.
5. **Before real use:** HTTPS for the portal, TURN server for remote candidates, email (SMTP), a lawyer's review of the consent text and certificate wording (India DPDP Act), and dataset licence review.
6. **Real-browser test of the interview portal:** HR in one browser profile and a candidate in another (or a second computer). Walk through scheduling, login, consent, screen sharing, and stopping sharing.

---

## 8. Problems we hit and their fixes

| Symptom | Cause | Fix (already applied) |
|---|---|---|
| `Fetching 0 files` for faces | Dataset ships archives (`.zip`/`.rar`), not images | Downloader extracts the archives |
| Scene model AUC 0.44 (worse than chance) | Dataset stored sorted; sample covered only some generators | Sampler now takes equal share per generator |
| `Tried to step 38 times...` | Old checkpoint with a different schedule was resumed | Old checkpoints ignored if settings differ |
| Document model saved as `face.pth` | Notebook kept old command-line settings between runs (`sys.argv`) | Script no longer uses `sys.argv`; quick runs save as `*_quick.pth` |
| `can't open file '/content/train_...py'` | Runtime restarted and wiped uploads | Upload the script again |
| `pyarrow requires NumPy 2` (local) | Version clash | Venv uses NumPy 2 |
| ONNX export crash on Windows | New exporter prints an emoji | Exporter uses the stable mode |
| Remote reads from Hugging Face hang on this PC | Network | Run data steps in Colab, not locally |

**Check before every run:** is the uploaded file the newest copy from `D:\HR Bot\colab\`? Is the GPU on? Did the log print the **right task name**?

---

## 9. Environment variables

| Variable | Meaning | Default |
|---|---|---|
| `VERIFYOPS_API_KEYS` | Comma-separated API keys | `dev-key` (change it) |
| `VERIFYOPS_PUBLIC_URL` | Base URL used in meeting links | `http://localhost:8000` |
| `VERIFYOPS_DATA` | Database, certificates, signing key folder | `data` |
| `VERIFYOPS_MODEL_DIR` | Where the `.onnx` files live | `models` |
| `VERIFYOPS_PASS_AT` / `VERIFYOPS_BLOCK_BELOW` | Verdict thresholds | 70 / 30 |
| `VERIFYOPS_DUP_DISTANCE` | Duplicate-photo sensitivity (lower = stricter) | 6 |
| `VERIFYOPS_EXIF_SKEW_HOURS` / `VERIFYOPS_GPS_MAX_KM` | Photo time/location tolerance vs device ping | 48 / 1.0 |
| `VERIFYOPS_WEBHOOK_HOSTS` | Allowed webhook hostnames | none |
| `VERIFYOPS_ICE` | STUN/TURN list for video | Google public STUN |
| `VERIFYOPS_TURN_USER`, `VERIFYOPS_TURN_PASS` | TURN login | none |
| `VERIFYOPS_SMTP_HOST/PORT/USER/PASS/FROM` | Email invitations | not set (copy link manually) |

---

## 10. Commands cheat sheet

```powershell
.\.venv\Scripts\Activate.ps1                              # enter the environment
python -m pytest -q                                       # run tests
uvicorn app.main:app --port 8000                          # start server
python scripts\create_user.py EMAIL "Name" "password"     # new HR login
python scripts\export_onnx.py FILE.pth --out DIR          # make ONNX
python scripts\eval_folder.py --task face --data DIR --model_dir DIR2   # independent test
docker compose up --build                                 # packaged run
```

**Never share or commit:** `data\signing_key.pem` (signs certificates), `.env`, API keys, user passwords.
