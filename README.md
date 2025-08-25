# QuizGo App

Welcome to **QuizGo** – an intelligent quiz generator and battle platform!

[![Hosted on Render](https://img.shields.io/badge/Live%20Demo-QuizGo-blue?style=for-the-badge)](https://quizgo-app-2.onrender.com/)

---

## 🚀 Live Demo

👉 **Try it now:** [https://quizgo-app-2.onrender.com/](https://quizgo-app-2.onrender.com/)

---

## 📚 Features

- **Quiz Generation:** Instantly generate quizzes from your own PDF documents.
- **Battle Mode:** Compete with friends or random users in real-time quiz battles.
- **Result Tracking:** View and download your battle results.
- **User-Friendly Interface:** Simple, clean, and responsive design.

---

## 🛠️ How It Works

1. **Upload a PDF:** The app extracts questions from your document.
2. **Generate Quiz:** Get a set of questions automatically.
3. **Start a Battle:** Challenge others and answer questions in real-time.
4. **View Results:** See your performance and download results as JSON.

---

## 🖥️ Tech Stack

- **Backend:** Python (Flask)
- **Frontend:** HTML, CSS (Jinja2 templates)
- **PDF Parsing:** PyPDF2
- **Hosting:** Render.com

---

## 📦 Installation (Local)

1. Clone the repository:
   ```bash
   git clone https://github.com/sumitaiml/quizgo-app-skillcred.git
   cd quizgo-app-skillcred
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python app.py
   ```
4. Open your browser at [http://localhost:5000](http://localhost:5000)

---

## 📁 Project Structure

```
├── app.py                  # Main Flask app
├── quiz_generator.py       # Quiz generation logic
├── requirements.txt        # Python dependencies
├── templates/              # HTML templates
├── uploads/                # Uploaded PDFs
├── battle_uploads/         # Battle PDFs
├── battle_results/         # Battle results (JSON)
├── results/                # Quiz results
└── ...
```

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

This project is licensed under the MIT License.

---

## 🌐 Author

- [Sumit AI ML](https://github.com/sumitaiml)

---

Enjoy using **QuizGo**! 🚀
