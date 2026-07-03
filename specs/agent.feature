Feature: SmartFarm Crop Advisory Agent
  As a farmer
  I want to interact with SmartFarm using text, voice, and images
  So that I can diagnose crop diseases, view weather warnings, check disease severity, translate results to Hindi, view history, and export PDF reports.

  Scenario: Diagnosing a crop disease using text description
    Given the farmer is on the SmartFarm home page
    When the farmer enters the crop issue: "My cotton crop in Surat, Gujarat has wilting leaves even though I water it. The leaves are yellowing from the bottom and there is white powder on the stems in late June."
    And the farmer submits the form
    Then the system should display a structured diagnosis report
    And the report must contain "🌾 Crop: Cotton"
    And the report must contain a 1-sentence cause
    And the report must contain exactly 3 immediate action steps
    And the report must contain exactly 2 prevention tips
    And the report must contain the helpline number "1800-180-1551"

  Scenario: Multimodal crop disease diagnosis with image upload
    Given the farmer is on the SmartFarm home page
    When the farmer uploads a crop photo "cotton_wilt.jpg"
    And the farmer enters the crop issue: "Leaves are turning yellow from the base of the stems"
    And the farmer submits the form
    Then the system should display the image preview in the results panel
    And the system should call the Gemini Vision API to analyze both image and text
    And the system should display the correct disease diagnosis report

  Scenario: Voice input transcription using Web Speech API
    Given the farmer is on the SmartFarm home page
    When the farmer selects language "🇮🇳 हिंदी"
    And the farmer clicks the microphone button
    And the farmer speaks: "मेरे कपास के पौधे सूख रहे हैं"
    Then the system should transcribe the speech and fill the text area with "मेरे कपास के पौधे सूख रहे हैं"

  Scenario: Severity rating colored progress bar display
    Given the farmer is on the SmartFarm home page
    When the farmer submits a description of a highly destructive disease like "Rice Blast"
    Then the system should show the disease severity as "High"
    And the system should display an orange progress bar and severity badge in the results panel

  Scenario: Local diagnosis history tracking and retrieval
    Given the farmer is on the SmartFarm home page
    When the farmer submits a diagnosis for a "Tomato Leaf Curl" issue
    Then the system should save the diagnosis in the local "history.json" file
    And the "Recent Diagnoses" section should list "Tomato Leaf Curl" as a clickable history card
    When the farmer clicks on the history card
    Then the system should display the full saved diagnosis report without calling the API again

  Scenario: Favorable weather context warning display
    Given the farmer is on the SmartFarm home page
    When the farmer submits the issue: "My cotton crop in Surat is wilting in late June"
    Then the system should fetch the current weather for "Surat"
    And the system should display current temperature, humidity, and precipitation in the weather widget
    And the report should include a warning note if weather conditions are favorable for the disease to spread

  Scenario: Exporting diagnosis report to PDF format
    Given the farmer has received a crop diagnosis report
    When the farmer clicks the "Download Report PDF" button
    Then the system should generate a PDF file containing:
      | Section | Content |
      | Logo | SmartFarm Logo |
      | Disease Name | The diagnosed disease |
      | Cause | The 1-sentence cause |
      | Actions | 3 immediate action steps |
      | Prevention | 2 prevention tips |
      | Helpline | Kisan Call Center: 1800-180-1551 |
    And the system should download the PDF file to the farmer's device

  Scenario: Translating diagnosis report to Hindi
    Given the farmer has received a crop diagnosis report in English
    When the farmer clicks the "🔄 Show in Hindi" button
    Then the system should translate the entire report to Hindi using the Gemini API
    And the results panel should display all text in Hindi script (Devanagari)
