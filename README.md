# README

This README provides step-by-step instructions for installing and running the Cult-Design-Scraper on **Windows (Command Prompt)** using a Python virtual environment.

---

## 1. Clone the repository

Open Command Prompt and run:

```cmd
git clone git@github.com:Malmqvistarn/Cult-Design-Scraper.git
cd Cult-Design-Scraper
```

---

## 2. Create a virtual environment

Run:

```cmd
py -m venv venv
```

This will create a `venv` folder in the project directory.

---

## 3. Activate the virtual environment

Run:

```cmd
env\Scripts\activate.bat
```

After activation, your prompt will start with `(venv)`.

---

## 4. Install dependencies

Run:

```cmd
pip install -r requirements.txt
```

---

## 5. Run the scraper

With the environment activated, run:

```cmd
python scraper.py
```

---

## 6. Deactivate the virtual environment

When finished, run:

```cmd
deactivate
```

---
