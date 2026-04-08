# OutSystems ODC Associate Developer - Practice Exam Simulator

A professional-grade Flask-based exam simulator for the OutSystems ODC Associate Developer certification. Features 50 scenario-based multiple-choice questions with a realistic exam interface, 120-minute timer, and detailed results analysis.

## Features

- **50 Comprehensive Questions** across 6 major categories
  - UI Design (15 questions)
  - Fetching Data (10 questions)
  - Logic (10 questions)
  - Web Apps in ODC (6 questions)
  - Data Modeling (6 questions)
  - Role-based Security (3 questions)

- **Professional Exam UI**
  - Dark sidebar with question navigator
  - Progress tracking and visual indicators
  - Color-coded category badges
  - Flag questions for review
  - Responsive design

- **120-Minute Countdown Timer**
  - Prominent display at top of screen
  - Visual warning at 10 minutes (yellow)
  - Critical alert at 5 minutes (red, pulsing)
  - Auto-submit when time expires

- **Intelligent Question Shuffling**
  - Questions randomized per session
  - Server-side answer validation
  - Session-based (no database needed)

- **Comprehensive Results**
  - Pass/Fail status (70% = 35/50 to pass)
  - Category breakdown with percentages
  - Full export of answers in text format
  - Copy-to-clipboard for Claude grading

## Quick Start

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Installation & Running

```bash
cd outsystems-exam

# Option 1: Using the run.sh script
./run.sh

# Option 2: Manual installation
pip install -r requirements.txt
python app.py
```

Then open your browser to: `http://localhost:5000`

## File Structure

```
outsystems-exam/
├── app.py                 # Flask application with 50 questions
├── templates/
│   └── index.html         # Complete exam UI and JavaScript
├── requirements.txt       # Python dependencies
├── run.sh                # Convenience startup script
└── README.md             # This file
```

## Question Coverage

### UI Design (15 questions)
- **Input Widgets (7)**: Form properties, validations, binding, mandatory fields
- **Blocks & Events (4)**: Block event handlers, mandatory events, parameter changes
- **Display Data Widgets (2)**: Expression widgets, data path binding
- **Pagination & Sorting (2)**: StartIndex, OnSort event, sorting logic

### Fetching Data (10 questions)
- **Aggregates (6)**: Filters (AND/OR), joins, hidden columns, calculated attributes, grouping, pattern matching
- **Fetching Data on Screens (4)**: Default fetch, On Demand, After Fetch, multiple Aggregates, data binding

### Logic (10 questions)
- **Logic Flows & Exception Handling (5)**: Switch/If statements, exception handlers, propagation, specific vs generic exceptions
- **Form Validations (3)**: Built-in validations, validation timing, Form.Valid checking
- **Client & Server Actions (2)**: Execution context, call direction, properties

### Web Apps in ODC (6 questions)
- **Screen Lifecycle (3)**: Initialize, Ready, Render, Destroy event order
- **App Troubleshooting (2)**: Breakpoints, debugging configuration
- **Client Variables (1)**: Session persistence, storage

### Data Modeling (6 questions)
- **Entities & Static Entities (3)**: Table mapping, ID attribute, Static Entity use cases
- **Data Relationships (2)**: 1-to-1, 1-to-Many, Many-to-Many reference attributes
- **Bootstrap from Excel (1)**: Data import timer, CreateOrUpdate logic

### Role-based Security (3 questions)
- Screen access control, role checking, dynamic visibility

## Exam Features

### Navigation
- Click any question number in the sidebar to jump to it
- Previous/Next buttons for sequential navigation
- Visual indicators: answered questions (green), current (blue), flagged (flag emoji)

### Question Flagging
- Flag questions for review without answering
- Visual flag indicator in the sidebar
- Helps identify difficult questions for later review

### Timer Display
- Always visible in the top-right corner
- Format: MM:SS (minutes:seconds)
- Color changes:
  - Normal: White (>10 minutes)
  - Warning: Yellow (10-5 minutes)
  - Critical: Red with pulsing animation (<5 minutes)

### Results Screen
- Final score and pass/fail status
- Category-by-category breakdown with percentages
- Export button to copy all answers

### Export Format
When you click "Copy All Answers to Clipboard," the output includes:
- Exam date and final score
- All 50 questions with:
  - Category and subcategory
  - Full question text
  - All four options (A-D)
  - Your selected answer (marked with >>>>>)
- Clean, readable text format

**Note**: The export does NOT include correct answers—it's designed for you to paste into Claude or another AI for detailed grading and feedback.

## How It Works

### Server-Side
1. Flask app stores 50 questions with correct answers
2. Questions are shuffled and stored in the session on first load
3. Answers are saved asynchronously as you select them
4. Grading happens server-side for security
5. Results returned with category breakdown

### Client-Side
1. HTML/CSS provides professional exam UI
2. JavaScript handles navigation, timer, and interaction
3. Questions and options displayed without answers visible
4. WebSocket-like fetch calls for synchronous saves
5. Results screen shows comprehensive analysis

## Customization

### Adding Questions
Edit `app.py` and add dictionaries to `EXAM_QUESTIONS` list:

```python
{
    'id': 51,
    'category': 'Your Category',
    'subcategory': 'Your Subcategory',
    'question': 'Your question text?',
    'options': [
        'A) Option 1',
        'B) Option 2',
        'C) Option 3',
        'D) Option 4'
    ],
    'correct': 'B',
    'explanation': 'Why B is correct...'
}
```

### Modifying Exam Duration
In `app.py`, change the default time (line with `7200`):
```python
7200  # 120 minutes in seconds
3600  # 60 minutes
```

### Changing Passing Score
In `app.py`, modify the passing threshold in `submit_exam()`:
```python
passed = percentage >= 70  # Change 70 to your desired percentage
```

## Question Design

All questions are designed to be:
- **Scenario-based**: Real-world situations, not just definitions
- **Exam-realistic**: Tricky options, common misconceptions
- **Specific**: Test actual ODC knowledge, not general web development
- **Detailed**: Include technical context and requirements

Example scenario-based question:
> "You configured an Aggregate with two filters: Status = 'Active' AND Priority = 'High'. If both conditions must be true, which logical operator is used?"

Rather than simple definitions:
> "What are filters in Aggregates?"

## Technical Details

- **Framework**: Flask (Python web framework)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Storage**: Flask session (server-side)
- **API**: RESTful endpoints for questions, answers, grading
- **No Database**: All state managed in session
- **No External Libraries**: Only Flask required

## Browser Compatibility

- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Desktop recommended for best experience due to sidebar layout.

## Troubleshooting

### Port Already in Use
If port 5000 is in use, modify `app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Change to different port
```

### Questions Not Loading
- Check browser console (F12) for errors
- Ensure Flask is running without errors
- Refresh the page

### Timer Issues
- Timer syncs with server on page load
- If out of sync, refresh the page
- Auto-submit triggers at 0:00

### Answers Not Saving
- Check network tab in browser console
- Ensure server is responding
- Try a different question and return

## License

This exam simulator is provided as-is for practice purposes.

## Support

For issues or questions about the simulator, check that:
1. Flask is installed: `pip install flask`
2. You're running from the correct directory
3. Browser is up to date
4. No browser extensions interfere with the page

---

**Good luck on your OutSystems ODC Associate Developer certification!**
