# 🔰 FraudGuard — Complete Beginner's Guide (Step-by-Step)

Welcome to **FraudGuard**! This guide is written so that **anyone** (even a complete beginner with zero coding background) can run, test, upload files, and interact with all 6 AI agents easily.

---

## 💡 What is FraudGuard?

Imagine you work at a bank, and you suspect someone is trying to steal money or commit fraud. Instead of checking everything manually, you have **6 specialized AI assistants** ready to help you 24/7:

| AI Agent | Name | Role | Example Question You Can Ask |
| :--- | :--- | :--- | :--- |
| 👩‍💼 | **Donna** | The Manager / Router | *"Help me with suspicious activity on my account."* |
| ⚖️ | **Harvey** | Fraud Analyst | *"Analyze transaction TX-999 for high velocity or fraud."* |
| 📜 | **Louis** | Compliance & AML Specialist | *"What are the legal AML rules for transferring $50,000?"* |
| 🕸️ | **Jessica** | Fraud Network Detective | *"Check if account A and account B belong to a fraud ring."* |
| 🛡️ | **Mike** | AI Security Tester | *"Test our fraud rules against hacker injection attacks."* |
| 📊 | **Rachel** | Data Engineer | *"Convert transaction logs into vector search embeddings."* |

---

## 🚀 Step 1: How to Start the App (2 Commands)

Open your computer's **PowerShell** (or Terminal) and run these two commands:

### Command 1: Start the Backend AI Engine
```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python.exe -m uvicorn fraudai.api.app:create_app --factory --host 0.0.0.0 --port 8000
```
*(Leave this terminal window open. It runs the backend server at `http://localhost:8000`)*

### Command 2: Start the Web Dashboard
Open a **second PowerShell window**, navigate to `frontend`, and run:
```powershell
cd frontend
npm run dev
```
*(Leave this terminal open too. It runs the visual website at `http://localhost:3000`)*

---

## 📁 Step 2: How to Upload Files for AI Analysis

You can upload files like **CSV transaction spreadsheets**, **JSON logs**, or **PDF legal documents** for the AI agents to analyze!

### Method A: Uploading via Swagger UI (Visual Button Click)
1. Open your browser to: **[http://localhost:8000/docs](http://localhost:8000/docs)**
2. Scroll down to the green endpoint: **`POST /api/v1/files/upload`** (Upload File).
3. Click on **`POST /api/v1/files/upload`** to open it.
4. Click the **Try it out** button on the top right of that box.
5. Click **Choose File** (Browse) and select your `.csv`, `.json`, or `.txt` file.
6. Click the big blue **Execute** button!
7. You will see a green response: `200 OK` with a message that your file has been ingested into the Qdrant vector database!

### Method B: Uploading via PowerShell (One Line)
If you prefer running a command, open PowerShell and run:
```powershell
# Get a login token
$tokenResp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/token" -Method Post -Body @{ username = "qa_analyst"; password = "password123" }
$headers = @{ Authorization = "Bearer $($tokenResp.access_token)" }

# Upload sample file
$form = @{ file = Get-Item "C:\path\to\your\file.csv" }
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/ingest" -Method Post -Headers $headers -Form $form
```

---

## 💬 Step 3: How to Chat with the AI Agents

1. Open your web browser and go to: **[http://localhost:3000](http://localhost:3000)**
2. Look at the bottom-left corner: You will see a green dot saying **"All systems operational"**.
3. **Try typing these questions into the chat box:**

### 1. Test Automatic Routing (Donna):
* Type: `"Analyze transaction TX-999 for suspicious velocity."`
* Press **Enter**.
* **What happens:** Donna reads your message, sees it is about transactions, and automatically assigns **Harvey Specter** to reply!

### 2. Test Compliance Rules (Louis):
* Click on **Louis** on the left sidebar.
* Type: `"What are the AML and KYC requirements for transferring large sums of money?"`
* Press **Enter**.
* **What happens:** Louis gives you a breakdown of regulatory laws.

### 3. Test Network Investigation (Jessica):
* Click on **Jessica** on the left sidebar.
* Type: `"Check if account ACC-101 and ACC-102 share the same IP address or device."`
* Press **Enter**.
* **What happens:** Jessica analyzes graph networks to detect money mule clusters.

---

## ⚡ Step 4: How to Run the Automated Test Script

Want to verify every single feature in 5 seconds without clicking?

Open PowerShell and run:
```powershell
.\test_demo.ps1
```

**What it will show you:**
```text
==================================================
   FraudGuard Full System Automated QA Verification
==================================================
[1/7] Testing System Health Endpoint... -> Status: healthy
[2/7] Authenticating User & Generating JWT Token... -> Token Issued!
[3/7] Testing Agent: Harvey Specter (Transaction Fraud)... -> Success!
[4/7] Testing Agent: Louis Litt (AML & Compliance)... -> Success!
[5/7] Testing Agent: Jessica Pearson (Fraud Graph Networks)... -> Success!
[6/7] Testing Agent: Mike Ross (Red Teaming Security)... -> Success!
[7/7] Testing Agent: Rachel Zane (Data Engineering & Vectors)... -> Success!
==================================================
   ✅ ALL 7 CORE FEATURES PASSED VERIFICATION!
==================================================
```

---

## ❓ Frequently Asked Questions (FAQ)

* **Q: Why does `http://localhost:8000` redirect to `/docs`?**  
  *A: `/docs` is where the interactive Swagger API documentation lives!*

* **Q: What if I see "Unauthorized" error when testing APIs manually?**  
  *A: Core endpoints require a JWT security token. Follow Method B in Step 2 or use `test_demo.ps1` which handles authentication automatically.*

---

*Created for FraudGuard by Yugam Nanda*
