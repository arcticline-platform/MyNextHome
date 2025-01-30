# Contributor Guidelines for MyNextHome

Thank you for your interest in contributing to **MyNextHome**! We welcome and appreciate your help in making this open-source real estate platform even better.

---

## How to Contribute

### 1. Fork & Clone the Repository

1. Fork the repository on GitHub.
2. Clone your forked repository to your local machine:
   
   ```sh
   git clone https://github.com/arcticline-platform/MyNextHome.git
   cd mynexthome
   ```

### 2. Set Up the Development Environment

- Ensure you have the required dependencies installed (see [README](README.md)).
- Create a virtual environment and install dependencies:
  
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```
- Set up the database:
  
   ```sh
   python manage.py makemigrations
   python manage.py migrate
   ```
- Run the development server:
  
   ```sh
   python manage.py runserver
   ```

### 3. Create a Feature Branch

1. Create a new branch for your feature or bugfix:
   
   ```sh
   git checkout -b feature-branch-name
   ```
2. Make your changes and commit them:
   
   ```sh
   git add .
   git commit -m "Add description of changes"
   ```

### 4. Run Tests

Ensure all tests pass before submitting a pull request:

```sh
pytest
```

### 5. Submit a Pull Request

1. Push your changes to your forked repository:
   
   ```sh
   git push origin feature-branch-name
   ```
2. Open a pull request (PR) on GitHub.
3. Provide a clear description of the changes in the PR.
4. Wait for review and address any feedback.

---

## Code Guidelines

- Follow **PEP 8** for Python code.
- Use **black** for code formatting:
  
   ```sh
   black .
   ```
- Write **unit tests** for new features and fixes.
- Document code using Python docstrings.

---

## Issue Reporting

If you encounter a bug or have a feature request:
1. Check [open issues](https://github.com/arcticline-platform/MyNextHome/issues) to avoid duplicates.
2. Open a new issue with a descriptive title.
3. Provide details including steps to reproduce, expected vs actual behavior, and screenshots if applicable.

---

## Contributor License Agreement (CLA)

By contributing, you agree that your code follows the project's license (**GNU GPL-3.0**). Your contributions remain open-source under this license.

---

## Community & Support

For discussions and support:
- Open a GitHub Discussion
- Email us at [info@daraza.net](mailto:info@daraza.net])

Thank you for contributing to **MyNextHome**! 🚀

