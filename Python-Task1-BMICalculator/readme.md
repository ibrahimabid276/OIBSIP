# BMI Calculator

## Overview

The BMI Calculator is a Python application that calculates a user's Body Mass Index (BMI) based on their height and weight. It supports both Command Line Interface (CLI) and Graphical User Interface (GUI) modes. The application stores BMI records in a SQLite database and allows users to view their BMI history through a trend chart.

## Objective

The objective of this project is to develop a BMI Calculator that accurately calculates BMI, categorizes health status and maintains a history of user records for progress tracking.

## Features

- Supports both CLI and GUI modes
- Calculates Body Mass Index (BMI)
- Displays BMI category (Underweight, Normal, Overweight or Obese)
- Stores BMI records in a SQLite database
- Maintains user BMI history
- Displays BMI trend chart using Matplotlib
- Validates user input
- Handles database and input errors gracefully

## Technologies Used

- Python
- Tkinter
- SQLite
- Matplotlib
- datetime

## Installation

Install the required dependency:

```bash
pip install matplotlib
```

## Usage

Run the application:

```bash
python main.py
```

Choose one of the following modes:

- CLI (Command Line Interface)
- GUI (Graphical User Interface)

Enter your name, weight and height to calculate your BMI. In GUI mode, your records are automatically saved, and you can view your BMI history using the trend chart.

## Author

**Syed Muhammad Ibrahim**

Python Programming Internship

Oasis Infobyte (OIBSIP)
