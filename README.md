<div align="center">
  <h1>🌐 Website Cloner</h1>
  <p><strong>A high-fidelity web cloning engine powered by Playwright and Google Gemini.</strong></p>
</div>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white">
  <img alt="Playwright" src="https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white">
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white">
  <img alt="Tailwind CSS" src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white">
</p>

This project is a sophisticated, full-stack application designed to clone any website with precision. It features a powerful FastAPI backend and a sleek Next.js frontend, offering multiple strategies for web content replication.

---

##  Core Features

-   **Dual Cloning Engines**: Choose between two powerful methods for website replication.
-   **High-Fidelity Capture**: Utilizes **Playwright** to run a headless browser, perfectly capturing complex, JavaScript-heavy websites with all their dynamic states and styles.
-   **AI-Powered Reconstruction**: Leverages **Google's Gemini** to intelligently analyze a website's DOM and semantically reconstruct a clean, lightweight HTML version.
-   **High-Performance API**: Built with **FastAPI** for asynchronous, non-blocking performance, ensuring rapid processing of cloning requests.
-   **Sleek, Modern UI**: A responsive and intuitive user interface built with **Next.js** and **Tailwind CSS**.
-   **Instant Preview and Copy option**: Preview and copy the generated HTML directly in the browser before downloading.

---

## 🛠️ Technology Showcase

This project is built on a foundation of powerful, modern technologies chosen for their performance and capabilities.

### Backend Architecture

-   **FastAPI**: High-performance Python framework for building the core API with a fully asynchronous pipeline.
-   **Pydantic**: Handles robust data validation, serialization, and automatic generation of schemas.
-   **Swagger UI**: Provides automatic, interactive API documentation, accessible directly from the browser.
-   **Playwright & Selenium**: A dual suite of browser automation tools. Playwright is used for its modern async capabilities, while Selenium provides industry-standard robustness for complex automation tasks.
-   **Google Gemini**: The AI-powered cloning engine; leverages advanced language model capabilities for semantic HTML reconstruction.
-   **BeautifulSoup4 & Requests**: Powerful and forgiving HTML/XML parser used for data extraction and structural analysis.
-   **Concurrent Futures**: Implements parallel processing to fetch external assets (like CSS) simultaneously, drastically reducing clone time.
-   **Uvicorn**: A lightning-fast ASGI server, essential for running the high-performance asynchronous application.

### Frontend Architecture

-   **Next.js**: A production-grade React framework that provides a robust structure for our frontend, including the App Router for modern routing and server components.
-   **TypeScript**: Ensures our frontend code is type-safe, scalable, and easier to maintain.
-   **Tailwind CSS**: A utility-first CSS framework that enables the creation of a bespoke, modern design system without writing a single line of custom CSS. It allows for rapid prototyping and a consistent visual language.

---

## 🚀 Getting Started

The entire application can be launched with a single command using the provided shell script.

### 1. Configure Environment

The backend requires a Google Gemini API key to function.

-   Navigate to the `backend` directory.
-   Create a `.env` file (`backend/.env`).
-   Add your API key to the file:
    ```
    GOOGLE_API_KEY="YOUR_GEMINI_API_KEY"
    ```

### 2. Launch the Application

The `start.sh` script automates the entire setup process.

-   **Make the script executable:**
    ```bash
    chmod +x start.sh
    ```
-   **Run the script:**
    ```bash
    ./start.sh
    ```

This command will handle all dependencies, configurations, and server startups for both the backend and frontend.

-   **Backend API**: `http://localhost:8000`
-   **API Docs (Swagger)**: `http://localhost:8000/docs`
-   **Frontend UI**: `http://localhost:3000`

---

## Troubleshooting

-   If the UI appears unstyled, the `start.sh` script may have been interrupted. It's crucial that it runs to completion, as it sets up the necessary configurations (`postcss.config.js` and `tailwind.config.js`).
-   For `npm` permission errors, ensure you have ownership of the project directory by running `sudo chown -R $USER:$USER .` from the project root.
