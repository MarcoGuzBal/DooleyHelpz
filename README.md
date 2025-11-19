

# DooleyHelpz

### *AI-Powered Course Planning for Emory Students*

Built by **DooleyDevs**

---

## Overview

**DooleyHelpz** is a full-stack web application designed to help Emory students automatically parse their transcripts, track degree progress, set academic preferences, and generate personalized semester schedules.

This project aims to simplify academic planning, streamline advising, and give students a smarter way to visualize their path to graduation.

---

## Tech Stack

### **Frontend**

* React + TypeScript
* Vite
* TailwindCSS
* Firebase 
* Hosted on **Vercel**

### **Backend**

* Python Flask
* Hosted on **Fly.io**

### **Database**

* MongoDB 

---

## Installation & Local Development

### ** 1. Clone the Repository**

```bash
git clone https://github.com/<your-org>/DooleyHelpz.git
cd DooleyHelpz
```

---

### ** 2. Frontend Setup**

```bash
cd frontend
npm install
npm run dev
```

The frontend will start at something like:

```
http://localhost:5173
```

---

### ** 3. Backend Setup (Flask)**

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The API will start at:

```
http://localhost:5000
```

---

## Environment Variables

### **Frontend `.env`**

```
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_STORAGE_BUCKET=
VITE_FIREBASE_MESSAGING_SENDER_ID=
VITE_FIREBASE_APP_ID=
VITE_BACKEND_URL=  # Example: https://<your-app>.fly.dev
```

### **Backend `.env`**

```
MONGODB_URI=
SECRET_KEY=
```

---

## Deployment

### **Frontend (Vercel)**

* Automatically builds from `main` branch
* Environment variables stored in Vercel dashboard

### **Backend (Fly.io)**

* Containerized Flask API
* Deployed via:

  ```bash
  fly deploy
  ```

### **Database (MongoDB)**

* Hosted on MongoDB Atlas
* Connected via `MONGODB_URI`

---

## Contributors

| Name                      | Role          | GitHub                                             |
| ------------------------- | ------------- | -------------------------------------------------- |
| **Marco Guzman-Balcazar** | Product Owner | [github.com/MarcoGuzBal](https://github.com/MarcoGuzBal) |
| **Anahi Perez**           | Scrum Master  | [github.com/anahip52](https://github.com/anahip52) |
| **Olivia Choi**           | Developer     | [github.com/eunbioli](https://github.com/eunbioli) |
| **Peteros Kahassay**      | Developer     | [github.com/Soretep-Yasshak](https://github.com/Soretep-Yasshak) |
| **Zimo Li**               | Developer     | [github.com/Z1M000](https://github.com/Z1M000) |


---

## Built with ❤️ by DooleyDevs

Let Us Know What you want!

Happy to refine it however you want!

