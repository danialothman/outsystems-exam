from flask import Flask, render_template, request, jsonify, session, redirect
from datetime import datetime, timedelta
import random
import json

app = Flask(__name__)
app.secret_key = 'outsystems-exam-simulator-2024'

# All 50 exam questions with correct answers
EXAM_QUESTIONS = [
    # UI DESIGN - Input Widgets (7 questions)
    {
        'id': 1,
        'category': 'UI Design',
        'subcategory': 'Input Widgets',
        'question': 'You are designing a form to capture customer information. The Form widget in ODC does NOT have which of the following properties?',
        'options': [
            'A) Source property',
            'B) Valid property',
            'C) Style properties',
            'D) Input child widgets'
        ],
        'correct': 'A',
        'explanation': 'Form widgets in ODC do NOT have a Source property. The Valid property aggregates the validity of all child input widgets. Style and input widgets are supported.'
    },
    {
        'id': 2,
        'category': 'UI Design',
        'subcategory': 'Input Widgets',
        'question': 'You have a form with mandatory field validation enabled on an Input widget. A user submits the form with an empty mandatory field. What happens?',
        'options': [
            'A) The action flow stops and prevents submission',
            'B) The action flow continues executing while the validation message displays',
            'C) An error dialog appears and the form is locked',
            'D) The database saves NULL value automatically'
        ],
        'correct': 'B',
        'explanation': 'Built-in validations do NOT stop action flow execution. The action continues even if inputs are invalid. You must check Form.Valid manually before saving.'
    },
    {
        'id': 3,
        'category': 'UI Design',
        'subcategory': 'Input Widgets',
        'question': 'You need to validate that a password field contains at least 8 characters and one uppercase letter. At what point should you check Form.Valid in your action?',
        'options': [
            'A) Before any custom validation logic',
            'B) In the middle of validation steps',
            'C) After the last custom validation',
            'D) Form.Valid is checked automatically'
        ],
        'correct': 'C',
        'explanation': 'Form.Valid aggregates child widget validity and should be checked AFTER all custom validations are complete to ensure comprehensive validation.'
    },
    {
        'id': 4,
        'category': 'UI Design',
        'subcategory': 'Input Widgets',
        'question': 'You have a Dropdown widget for selecting a country and a Button Group for selecting regions. Which property stores the selected value?',
        'options': [
            'A) Both use Variable property on each individual item',
            'B) Dropdown uses Variable, Button Group uses Variable on the group itself',
            'C) Both use SelectedItem property',
            'D) Dropdown has Source, Button Group has Items'
        ],
        'correct': 'B',
        'explanation': 'Dropdown widgets have a Variable property for the selected value. Button Group has Variable on the group itself, not on individual items.'
    },
    {
        'id': 5,
        'category': 'UI Design',
        'subcategory': 'Input Widgets',
        'question': 'You need to create a toggle for enabling/disabling notifications. Which input widgets can be bound to a Boolean variable? Select the scenario that applies.',
        'options': [
            'A) Only Checkbox can be bound to Boolean',
            'B) Only Switch can be bound to Boolean',
            'C) Both Checkbox and Switch can be bound to Boolean',
            'D) Neither - use Radio Button Group for Boolean values'
        ],
        'correct': 'C',
        'explanation': 'Both Checkbox and Switch widgets can be bound to Boolean variables. They are interchangeable for Boolean value selection.'
    },
    {
        'id': 6,
        'category': 'UI Design',
        'subcategory': 'Input Widgets',
        'question': 'A user completes a form and you want to visually indicate which fields are mandatory. What does ODC display on mandatory fields?',
        'options': [
            'A) A red asterisk and a bold label',
            'B) A red asterisk only',
            'C) The word "mandatory" next to the label',
            'D) A light gray background color'
        ],
        'correct': 'B',
        'explanation': 'Labels on mandatory fields display a red asterisk (*) as the visual cue to indicate the field is required.'
    },
    {
        'id': 7,
        'category': 'UI Design',
        'subcategory': 'Input Widgets',
        'question': 'You are configuring validation for a username field. Which of these is NOT a built-in validation in ODC input widgets?',
        'options': [
            'A) Mandatory field validation',
            'B) Data type validation',
            'C) Maximum length validation',
            'D) Format validation'
        ],
        'correct': 'C',
        'explanation': 'ODC input widgets support mandatory and data type validations. Maximum length is NOT a built-in validation - it must be implemented as custom logic.'
    },

    # UI DESIGN - Blocks & Events (4 questions)
    {
        'id': 8,
        'category': 'UI Design',
        'subcategory': 'Blocks & Events',
        'question': 'You created a reusable Block with a custom event. Where can you define event handlers for this Block event?',
        'options': [
            'A) At the Block level only',
            'B) At both Block and Screen level',
            'C) At the Screen level only',
            'D) In the OnInitialize handler'
        ],
        'correct': 'A',
        'explanation': 'Block events are defined at the Block level only, NOT at the Screen level. This provides clear separation of concerns.'
    },
    {
        'id': 9,
        'category': 'UI Design',
        'subcategory': 'Blocks & Events',
        'question': 'You defined a custom Block event with "Is Mandatory = Yes". What does this mean for parent screens/blocks that use this Block?',
        'options': [
            'A) The event handler is optional',
            'B) Every parent MUST define a handler for this event',
            'C) The event fires at least once per screen load',
            'D) The Block cannot be used without an active event'
        ],
        'correct': 'B',
        'explanation': 'When Is Mandatory = Yes, every parent must define a handler. When Is Mandatory = No, the handler is optional and created only where it makes sense.'
    },
    {
        'id': 10,
        'category': 'UI Design',
        'subcategory': 'Blocks & Events',
        'question': 'A Block receives input parameters from its parent screen. The parent screen changes the value of one input parameter. Which Block event triggers?',
        'options': [
            'A) OnInitialize',
            'B) OnParametersChanged',
            'C) OnDataChange',
            'D) OnReady'
        ],
        'correct': 'B',
        'explanation': 'OnParametersChanged triggers when the parent changes at least one Block Input Parameter. This allows the Block to react to parameter updates.'
    },
    {
        'id': 11,
        'category': 'UI Design',
        'subcategory': 'Blocks & Events',
        'question': 'You created a date picker Block and want to reuse it in multiple places. Can a Block be used inside itself?',
        'options': [
            'A) Yes, unlimited nesting is allowed',
            'B) Yes, but only one level deep',
            'C) No, a Block cannot be used inside itself',
            'D) No, but a Block can only be reused once'
        ],
        'correct': 'C',
        'explanation': 'Blocks can be used in Screens and other Blocks, but NOT inside itself. They can be reused multiple times across the app.'
    },

    # UI DESIGN - Display Data Widgets (2 questions)
    {
        'id': 12,
        'category': 'UI Design',
        'subcategory': 'Display Data Widgets',
        'question': 'You need to display a dynamically calculated value like "Total: $" + Sum(OrderAmount). Which widget should you use?',
        'options': [
            'A) Text widget',
            'B) Expression widget',
            'C) Label widget',
            'D) Paragraph widget'
        ],
        'correct': 'B',
        'explanation': 'Expression widget displays text calculated at runtime. It evaluates expressions like concatenation and arithmetic operations.'
    },
    {
        'id': 13,
        'category': 'UI Design',
        'subcategory': 'Display Data Widgets',
        'question': 'You want to use an expression in an Expression widget that returns a calculated discount percentage. What property must the Client Action have?',
        'options': [
            'A) Callable = Yes',
            'B) Function = Yes',
            'C) Expression = True',
            'D) Execute = Client'
        ],
        'correct': 'B',
        'explanation': 'Client Action with Function = Yes is required for use in Expression widgets. This allows the action to be invoked as a function in expressions.'
    },

    # UI DESIGN - Pagination & Sorting (2 questions)
    {
        'id': 14,
        'category': 'UI Design',
        'subcategory': 'Pagination & Sorting',
        'question': 'Your List widget shows records 10-20 on page 2. What does StartIndex = 10 represent in this pagination scenario?',
        'options': [
            'A) The total number of pages',
            'B) The page number being displayed',
            'C) The offset where the page starts',
            'D) The number of records per page'
        ],
        'correct': 'C',
        'explanation': 'StartIndex indicates where each page starts (offset), NOT the total pages. StartIndex = 10 means skip 10 records and start from record 11.'
    },
    {
        'id': 15,
        'category': 'UI Design',
        'subcategory': 'Pagination & Sorting',
        'question': 'A user clicks on the "Name" column header to sort. You need to capture which column was clicked. What parameter does the OnSort event provide?',
        'options': [
            'A) A boolean for ascending/descending',
            'B) The column index number',
            'C) An input parameter containing the clicked column',
            'D) The sort order as a string'
        ],
        'correct': 'C',
        'explanation': 'OnSort event has an input parameter containing the clicked column name. You use this to apply sorting logic to the Aggregate.'
    },

    # FETCHING DATA - Aggregates (6 questions)
    {
        'id': 16,
        'category': 'Fetching Data',
        'subcategory': 'Aggregates',
        'question': 'You configured an Aggregate with two filters: Status = "Active" AND Priority = "High". If both conditions must be true, which logical operator is used?',
        'options': [
            'A) OR - either condition can be true',
            'B) AND - both conditions must be true',
            'C) XOR - exactly one must be true',
            'D) NOT - inverts the conditions'
        ],
        'correct': 'B',
        'explanation': 'Multiple filters in Aggregates use AND logic. ALL filters must be true for a record to be included in results.'
    },
    {
        'id': 17,
        'category': 'Fetching Data',
        'subcategory': 'Aggregates',
        'question': 'You need to fetch customers and their orders, but include customers who may not have any orders. Which join type should you use?',
        'options': [
            'A) "Only With" - INNER JOIN',
            'B) "With or Without" - LEFT JOIN',
            'C) "Cross Join" - CROSS JOIN',
            'D) "Full Join" - FULL OUTER JOIN'
        ],
        'correct': 'B',
        'explanation': 'LEFT JOIN is configured with "With or Without" to include customers regardless of whether they have orders. INNER JOIN uses "Only With".'
    },
    {
        'id': 18,
        'category': 'Fetching Data',
        'subcategory': 'Aggregates',
        'question': 'You hid several columns in your Aggregate (not needed for display). What impact does this have on the Aggregate output?',
        'options': [
            'A) Hidden columns are removed from the output',
            'B) Hidden columns still appear in output and can be used',
            'C) Hidden columns only affect preview, still available in output',
            'D) Hiding columns improves query performance'
        ],
        'correct': 'C',
        'explanation': 'Hidden columns only affect the preview visualization. They are still available in the Aggregate output and can be referenced in expressions.'
    },
    {
        'id': 19,
        'category': 'Fetching Data',
        'subcategory': 'Aggregates',
        'question': 'You want to add a calculated attribute to an Aggregate that calls a Server Action to compute a commission value. Is this allowed?',
        'options': [
            'A) Yes, Server Actions execute during Aggregate evaluation',
            'B) No, calculated attributes cannot use Server Actions',
            'C) Yes, but only for read-only attributes',
            'D) No, Aggregates only support Entity attributes'
        ],
        'correct': 'B',
        'explanation': 'Calculated attributes in Aggregates cannot use Server Actions. Server Actions are asynchronous and not available during Aggregate evaluation.'
    },
    {
        'id': 20,
        'category': 'Fetching Data',
        'subcategory': 'Aggregates',
        'question': 'You configured an Aggregate with GroupBy on Department and an aggregation function SUM(Salary). What columns appear in the output?',
        'options': [
            'A) All columns from the source entity',
            'B) Only the SUM column',
            'C) Only the grouped columns and aggregation columns',
            'D) All columns plus a Count() column'
        ],
        'correct': 'C',
        'explanation': 'When using aggregation functions with GroupBy, output contains ONLY the grouped columns (Department) plus aggregation columns (SUM).'
    },
    {
        'id': 21,
        'category': 'Fetching Data',
        'subcategory': 'Aggregates',
        'question': 'You need to filter an Aggregate for products where Name contains "Premium". Which operator should you use?',
        'options': [
            'A) equals with "Premium"',
            'B) like with "%Premium%"',
            'C) contains with "Premium"',
            'D) matches with "Premium*"'
        ],
        'correct': 'B',
        'explanation': 'The "like" operator with % wildcard (like "%Premium%") is used for pattern matching in text filters.'
    },

    # FETCHING DATA - Fetching Data on Screens (4 questions)
    {
        'id': 22,
        'category': 'Fetching Data',
        'subcategory': 'Fetching Data on Screens',
        'question': 'You added an Aggregate to a screen but did not explicitly configure when to fetch data. What is the default behavior?',
        'options': [
            'A) On Demand - waits for manual refresh',
            'B) At Start - fetches automatically when screen loads',
            'C) After Screen - never fetches automatically',
            'D) On Focus - fetches when screen gains focus'
        ],
        'correct': 'B',
        'explanation': 'Default Fetch = "At Start" - data loads automatically when the screen initializes. "On Demand" requires explicit Refresh Data action.'
    },
    {
        'id': 23,
        'category': 'Fetching Data',
        'subcategory': 'Fetching Data on Screens',
        'question': 'You set an Aggregate to "On Demand" fetch. How do you refresh the data on the screen?',
        'options': [
            'A) Use the Data Refresh widget',
            'B) Add a Refresh Data node in a Screen Action',
            'C) Call the After Fetch event',
            'D) Change the Fetch setting to "At Start"'
        ],
        'correct': 'B',
        'explanation': 'Only "On Demand" requires a Refresh Data node in a Screen Action to fetch data. The Refresh Data node triggers the Aggregate execution.'
    },
    {
        'id': 24,
        'category': 'Fetching Data',
        'subcategory': 'Fetching Data on Screens',
        'question': 'After an Aggregate finishes fetching data, you need to execute a specific action. Which event should you use?',
        'options': [
            'A) OnDataFetched - Screen event',
            'B) After Fetch - Aggregate event',
            'C) OnScreenReady - Screen event',
            'D) AfterData - Global event'
        ],
        'correct': 'B',
        'explanation': '"After Fetch" is an Aggregate event (not a Screen/Block event) that executes after data fetching completes. This is the correct event to use.'
    },
    {
        'id': 25,
        'category': 'Fetching Data',
        'subcategory': 'Fetching Data on Screens',
        'question': 'A screen has three Aggregates: UserData (At Start), Orders (On Demand), and Analytics (At Start). How do they fetch?',
        'options': [
            'A) All three fetch at screen start',
            'B) Only UserData and Analytics fetch at start; Orders requires refresh',
            'C) All three require manual refresh',
            'D) Only UserData fetches; others need explicit calls'
        ],
        'correct': 'B',
        'explanation': 'Each Aggregate has independent Fetch settings. "At Start" fetches automatically; "On Demand" requires explicit Refresh Data action.'
    },

    # LOGIC - Logic Flows & Exception Handling (5 questions)
    {
        'id': 26,
        'category': 'Logic',
        'subcategory': 'Logic Flows & Exception Handling',
        'question': 'You have a Switch with branches for Status = "Pending", "Active", "Completed", and a Default branch. If Status = "Active", what happens?',
        'options': [
            'A) All matching branches execute',
            'B) Only the first matching branch executes',
            'C) Both "Active" and "Default" branches execute',
            'D) The Default branch only executes'
        ],
        'correct': 'B',
        'explanation': 'Switch executes only the FIRST matching branch. Once a match is found, subsequent branches are skipped.'
    },
    {
        'id': 27,
        'category': 'Logic',
        'subcategory': 'Logic Flows & Exception Handling',
        'question': 'You need to check if a user has admin role, then proceed differently. You try to add three branches to an If statement. What happens?',
        'options': [
            'A) All three branches are created successfully',
            'B) Only True and False branches exist; cannot add more',
            'C) A third branch appears as "Else If"',
            'D) The If statement converts to a Switch'
        ],
        'correct': 'B',
        'explanation': 'If statement has exactly 2 branches (True/False). You cannot add more branches - use Switch for multiple conditions.'
    },
    {
        'id': 28,
        'category': 'Logic',
        'subcategory': 'Logic Flows & Exception Handling',
        'question': 'You have a Server Action with exception handlers. Exception handler flow crosses another flow path. Is this allowed in ODC?',
        'options': [
            'A) Yes, exception handlers can cross any flow',
            'B) No, exception handler flows cannot intersect other flows',
            'C) Yes, but only with a Filter node between them',
            'D) No, exception handlers must use separate actions'
        ],
        'correct': 'B',
        'explanation': 'Exception handler flow cannot intersect other flows. They must remain separate and non-crossing for clarity and proper execution.'
    },
    {
        'id': 29,
        'category': 'Logic',
        'subcategory': 'Logic Flows & Exception Handling',
        'question': 'An action throws a DatabaseException. Multiple exception handlers exist: one for DatabaseException and one for AllExceptions. Which catches the error?',
        'options': [
            'A) Both handlers execute',
            'B) AllExceptions catches the error first',
            'C) DatabaseException (most specific) catches first',
            'D) The error is uncaught'
        ],
        'correct': 'C',
        'explanation': 'Most specific exception handler catches first. DatabaseException is more specific than AllExceptions, so it takes precedence.'
    },
    {
        'id': 30,
        'category': 'Logic',
        'subcategory': 'Logic Flows & Exception Handling',
        'question': 'An exception occurs in a Client Action that was called by a Server Action. What is the exception propagation path?',
        'options': [
            'A) Client Action → Screen → Database',
            'B) Client Action → Server Action → Global Exception Handler',
            'C) Client Action → Global Exception Handler directly',
            'D) Exceptions in Client Actions cannot propagate'
        ],
        'correct': 'B',
        'explanation': 'Exceptions bubble up: current action → calling action → Global Exception Handler. Server Action catches what Client Action throws.'
    },

    # LOGIC - Form Validations (3 questions)
    {
        'id': 31,
        'category': 'Logic',
        'subcategory': 'Form Validations',
        'question': 'A form has inputs for email and password. Which validations are considered "built-in" in ODC?',
        'options': [
            'A) Mandatory fields and data type matching only',
            'B) Mandatory, data type, and maximum length',
            'C) Mandatory, format, and email validation',
            'D) All of the above'
        ],
        'correct': 'A',
        'explanation': 'Built-in validations are ONLY mandatory field checking and data type validation. Maximum length must be custom logic.'
    },
    {
        'id': 32,
        'category': 'Logic',
        'subcategory': 'Form Validations',
        'question': 'A mandatory Input widget is empty. Built-in validation detects this. Does the input prevent data from being saved automatically?',
        'options': [
            'A) Yes, invalid inputs are blocked from saving',
            'B) No, built-in validations do NOT prevent saving automatically',
            'C) Yes, but only for mandatory fields',
            'D) Only if Form.Valid is checked'
        ],
        'correct': 'B',
        'explanation': 'Built-in validations do NOT prevent data from being saved. You must check Form.Valid before saving, regardless of validations.'
    },
    {
        'id': 33,
        'category': 'Logic',
        'subcategory': 'Form Validations',
        'question': 'A user enters invalid data in a form field. You did not configure any custom validation. What should you do before saving data?',
        'options': [
            'A) Trust the built-in validations',
            'B) Check Form.Valid, even without custom validations',
            'C) Save immediately - validations prevent issues',
            'D) Wait for the built-in validation message'
        ],
        'correct': 'B',
        'explanation': 'Form.Valid must ALWAYS be checked before saving, even without custom validations. This ensures comprehensive validation coverage.'
    },

    # LOGIC - Client & Server Actions (2 questions)
    {
        'id': 34,
        'category': 'Logic',
        'subcategory': 'Client & Server Actions',
        'question': 'You need to fetch sensitive data from a database and hide it from the browser. Should you use a Client Action or Server Action?',
        'options': [
            'A) Client Action - executes in the browser',
            'B) Server Action - executes on the server for security',
            'C) Both are equally secure',
            'D) Browser data is always protected'
        ],
        'correct': 'B',
        'explanation': 'Server Actions execute on the server and are appropriate for sensitive data access. Client Actions run in the browser and are less secure.'
    },
    {
        'id': 35,
        'category': 'Logic',
        'subcategory': 'Client & Server Actions',
        'question': 'A Client Action calls a Server Action. Can the Server Action call a Client Action in return?',
        'options': [
            'A) Yes, bidirectional calls are allowed',
            'B) No, Server Actions cannot call Client Actions',
            'C) Yes, but only with explicit permission',
            'D) Only if they are in the same module'
        ],
        'correct': 'B',
        'explanation': 'Client Actions CAN call Server Actions, but Server Actions CANNOT call Client Actions. The call direction is one-way.'
    },

    # WEB APPS IN ODC - Screen Lifecycle (3 questions)
    {
        'id': 36,
        'category': 'Web Apps in ODC',
        'subcategory': 'Screen Lifecycle',
        'question': 'A screen loads and you need to set a default value for a Local Variable. At which lifecycle stage should you do this?',
        'options': [
            'A) OnReady - DOM is available',
            'B) OnInitialize - before DOM is ready',
            'C) OnRender - after DOM is rendered',
            'D) OnDestroy - cleanup stage'
        ],
        'correct': 'B',
        'explanation': 'OnInitialize is the stage to set default values for Local Variables. DOM is not ready yet, but variables can be initialized.'
    },
    {
        'id': 37,
        'category': 'Web Apps in ODC',
        'subcategory': 'Screen Lifecycle',
        'question': 'You need to set focus on a specific Input widget when the screen loads. The DOM must be available. Which lifecycle event should you use?',
        'options': [
            'A) OnInitialize - variables can be set',
            'B) OnReady - DOM is available',
            'C) OnRender - rendering is complete',
            'D) OnDataBound - data is bound'
        ],
        'correct': 'B',
        'explanation': 'OnReady is when DOM is available and ready for manipulation. This is the proper stage to set widget focus or interact with DOM elements.'
    },
    {
        'id': 38,
        'category': 'Web Apps in ODC',
        'subcategory': 'Screen Lifecycle',
        'question': 'The correct order of screen lifecycle events is:',
        'options': [
            'A) Ready → Initialize → Render → Destroy',
            'B) Initialize → Ready → Render → Destroy',
            'C) Render → Initialize → Ready → Destroy',
            'D) Initialize → Render → Ready → Destroy'
        ],
        'correct': 'B',
        'explanation': 'Correct lifecycle order: Initialize → Ready → Render → Destroy. Initialize first, then ready (DOM available), render, then destroy.'
    },

    # WEB APPS IN ODC - App Troubleshooting (2 questions)
    {
        'id': 39,
        'category': 'Web Apps in ODC',
        'subcategory': 'App Troubleshooting',
        'question': 'You are debugging an app and need to check variable values during execution. Where can you set breakpoints in ODC?',
        'options': [
            'A) Screens only',
            'B) Server Actions only',
            'C) Client and Server Actions',
            'D) Anywhere in the app flow'
        ],
        'correct': 'C',
        'explanation': 'Breakpoints can be set in both Client and Server Actions. This allows inspection of variable values during debugging.'
    },
    {
        'id': 40,
        'category': 'Web Apps in ODC',
        'subcategory': 'App Troubleshooting',
        'question': 'You are debugging a consumer app that calls a producer module. How do you set the entry point for debugging?',
        'options': [
            'A) In the consumer app settings',
            'B) Set "Entry App" to the consumer in the producer',
            'C) Use "Restart Debugging" button',
            'D) Debug is automatic - no setup needed'
        ],
        'correct': 'B',
        'explanation': 'Set the "Entry App" in the producer to point to the consumer for debugging. "Restart Debugging" does NOT exist in ODC.'
    },

    # WEB APPS IN ODC - Client Variables (1 question)
    {
        'id': 41,
        'category': 'Web Apps in ODC',
        'subcategory': 'Client Variables',
        'question': 'You cache the current user name in a Client Variable. How long does this value persist?',
        'options': [
            'A) Until the browser tab closes',
            'B) Across screens within a session',
            'C) Permanently in browser storage',
            'D) Only within the current screen'
        ],
        'correct': 'B',
        'explanation': 'Client Variables persist across screens within a session, stored client-side. They are good for caching frequently accessed data like User Name.'
    },

    # DATA MODELING - Entities & Static Entities (3 questions)
    {
        'id': 42,
        'category': 'Data Modeling',
        'subcategory': 'Entities & Static Entities',
        'question': 'You created an Entity to store customer records. Where is this Entity data stored?',
        'options': [
            'A) In application memory',
            'B) In the browser localStorage',
            'C) In a database table',
            'D) In a static JSON file'
        ],
        'correct': 'C',
        'explanation': 'Entities map to database tables. Each Entity creates a corresponding table in the database for persistent data storage.'
    },
    {
        'id': 43,
        'category': 'Data Modeling',
        'subcategory': 'Entities & Static Entities',
        'question': 'You need a Status field with fixed values: "Pending", "In Progress", "Completed". Which should you use?',
        'options': [
            'A) Regular Entity with three records',
            'B) Static Entity for enumeration values',
            'C) A Text field with validation',
            'D) A separate Status table Entity'
        ],
        'correct': 'B',
        'explanation': 'Static Entities are enumerations with records modifiable at design time only. They are perfect for fixed enumeration values.'
    },
    {
        'id': 44,
        'category': 'Data Modeling',
        'subcategory': 'Entities & Static Entities',
        'question': 'An Entity has an auto-generated Id attribute. What role does this serve?',
        'options': [
            'A) Optional identifier for lookups',
            'B) Primary Key - uniquely identifies each record',
            'C) A system field that cannot be used',
            'D) For internal ODC use only'
        ],
        'correct': 'B',
        'explanation': 'Auto-generated Id attribute is the Primary Key. Each Entity automatically has this for uniquely identifying records.'
    },

    # DATA MODELING - Data Relationships (2 questions)
    {
        'id': 45,
        'category': 'Data Modeling',
        'subcategory': 'Data Relationships',
        'question': 'You have a 1-to-Many relationship: one Company has many Employees. How is this implemented?',
        'options': [
            'A) Company has an Employee reference attribute',
            'B) Employee has a Company reference attribute',
            'C) Both have reference attributes to each other',
            'D) A junction table is required'
        ],
        'correct': 'B',
        'explanation': 'In 1-to-Many, the detail entity (Employee) has a reference attribute of the master entity (Company) Identifier type.'
    },
    {
        'id': 46,
        'category': 'Data Modeling',
        'subcategory': 'Data Relationships',
        'question': 'You need to create a Many-to-Many relationship between Students and Courses. What is required?',
        'options': [
            'A) Add reference attributes to both Student and Course',
            'B) Create a junction Entity with references to both Student and Course',
            'C) A complex formula in the Aggregate',
            'D) Students and Courses must be in separate modules'
        ],
        'correct': 'B',
        'explanation': 'Many-to-Many requires a junction entity with two reference attributes pointing to both entities.'
    },

    # DATA MODELING - Bootstrap from Excel (1 question)
    {
        'id': 47,
        'category': 'Data Modeling',
        'subcategory': 'Bootstrap from Excel',
        'question': 'You want to import initial data from an Excel file into an Entity. What does the Bootstrap feature create?',
        'options': [
            'A) A manual data import dialog',
            'B) A Timer that runs on first publish to populate data',
            'C) An import API endpoint',
            'D) A bulk upload screen'
        ],
        'correct': 'B',
        'explanation': 'Bootstrap creates a Timer that executes on first publish, using CreateOrUpdate logic to populate initial data from Excel.'
    },

    # ROLE-BASED SECURITY (3 questions)
    {
        'id': 48,
        'category': 'Role-based Security',
        'subcategory': 'Role-based Security',
        'question': 'You want to restrict a screen to only authenticated users with "Admin" role. Where do you configure this?',
        'options': [
            'A) In the OnInitialize event',
            'B) Screen Properties → Accessible By → select roles',
            'C) Using a Server Action only',
            'D) In a global configuration file'
        ],
        'correct': 'B',
        'explanation': 'Screen Properties → Accessible By section allows you to specify roles. Select "Authenticated users" then choose specific roles.'
    },
    {
        'id': 49,
        'category': 'Role-based Security',
        'subcategory': 'Role-based Security',
        'question': 'A screen is protected with role-based security. A user tries to access it without the required role. What happens?',
        'options': [
            'A) The screen loads but displays a warning',
            'B) A redirect occurs and access is denied',
            'C) The screen loads but features are disabled',
            'D) An error message appears in the console'
        ],
        'correct': 'B',
        'explanation': 'Screen-level role-based security prevents access entirely. Users without required roles are redirected and access is denied.'
    },
    {
        'id': 50,
        'category': 'Role-based Security',
        'subcategory': 'Role-based Security',
        'question': 'You need to dynamically show/hide a widget based on user role at runtime. What approach is needed?',
        'options': [
            'A) Screen Properties security is sufficient',
            'B) Use CheckRole action in an If widget to conditionally display',
            'C) Use both screen authorization AND If widget with CheckRole',
            'D) Role-based visibility is not supported in ODC'
        ],
        'correct': 'C',
        'explanation': 'Both screen-level AND runtime security are recommended. Screen Properties protect the screen; CheckRole in an If widget controls widget visibility.'
    }
]

# Build a lookup dict for O(1) access by question id
QUESTIONS_BY_ID = {q['id']: q for q in EXAM_QUESTIONS}

def get_session_questions():
    """Get ordered question objects from session's ID list"""
    order = session.get('question_order', [])
    return [QUESTIONS_BY_ID[qid] for qid in order if qid in QUESTIONS_BY_ID]

@app.route('/')
def index():
    """Initialize exam session"""
    if 'question_order' not in session:
        ids = [q['id'] for q in EXAM_QUESTIONS]
        random.shuffle(ids)
        session['question_order'] = ids
        session['start_time'] = datetime.now().isoformat()
        session['answers'] = {}
        session['flagged'] = []
    return render_template('index.html')

@app.route('/api/questions')
def get_questions():
    """Get all questions without answers"""
    questions_for_client = []
    for q in get_session_questions():
        questions_for_client.append({
            'id': q['id'],
            'category': q['category'],
            'subcategory': q['subcategory'],
            'question': q['question'],
            'options': q['options']
        })
    return jsonify(questions_for_client)

@app.route('/api/submit', methods=['POST'])
def submit_exam():
    """Grade exam and return results"""
    data = request.get_json()
    user_answers = data.get('answers', {})

    questions = get_session_questions()
    score = 0
    results = []

    for question in questions:
        q_id = str(question['id'])
        user_answer = user_answers.get(q_id, '')
        is_correct = user_answer == question['correct']

        if is_correct:
            score += 1

        results.append({
            'id': question['id'],
            'category': question['category'],
            'subcategory': question['subcategory'],
            'question': question['question'],
            'options': question['options'],
            'correct': question['correct'],
            'user_answer': user_answer,
            'is_correct': is_correct
        })

    percentage = (score / len(questions)) * 100
    passed = percentage >= 70

    category_breakdown = {}
    for result in results:
        cat = result['category']
        if cat not in category_breakdown:
            category_breakdown[cat] = {'total': 0, 'correct': 0}
        category_breakdown[cat]['total'] += 1
        if result['is_correct']:
            category_breakdown[cat]['correct'] += 1

    return jsonify({
        'score': score,
        'total': len(questions),
        'percentage': round(percentage, 1),
        'passed': passed,
        'results': results,
        'category_breakdown': category_breakdown
    })

@app.route('/api/save-answer', methods=['POST'])
def save_answer():
    """Save user's answer"""
    data = request.get_json()
    q_id = str(data.get('question_id'))
    answer = data.get('answer')

    if 'answers' not in session:
        session['answers'] = {}

    answers = session['answers']
    answers[q_id] = answer
    session['answers'] = answers
    session.modified = True

    return jsonify({'success': True})

@app.route('/api/toggle-flag', methods=['POST'])
def toggle_flag():
    """Toggle question flag"""
    data = request.get_json()
    q_id = str(data.get('question_id'))

    if 'flagged' not in session:
        session['flagged'] = []

    flagged = list(session['flagged'])
    if q_id in flagged:
        flagged.remove(q_id)
    else:
        flagged.append(q_id)
    session['flagged'] = flagged
    session.modified = True

    return jsonify({'flagged': q_id in session['flagged']})

@app.route('/api/time-remaining')
def time_remaining():
    """Get remaining exam time"""
    if 'start_time' not in session:
        return jsonify({'remaining': 7200})

    start = datetime.fromisoformat(session['start_time'])
    elapsed = (datetime.now() - start).total_seconds()
    remaining = max(0, 7200 - elapsed)

    return jsonify({'remaining': remaining})

@app.route('/reset')
def reset():
    """Reset exam session"""
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
