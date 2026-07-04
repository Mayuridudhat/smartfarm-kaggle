Feature: SmartFarm Crop Advisory Agent

  Background:
    Given the SmartFarm agent is running
    And Gemini API is connected
    And Open-Meteo weather API is available

  Scenario: Farmer reports cotton crop disease
    Given a farmer types "My cotton crop in Surat Gujarat has wilting leaves and white powder on stems in late June"
    When the agent processes the input
    Then it should identify the disease as Collar Rot or Powdery Mildew
    And return cause, immediate action steps and prevention tips
    And show severity as High or Critical
    And display current weather for Surat
    And include Kisan helpline number 1800-180-1551

  Scenario: Farmer reports rice crop disease
    Given a farmer types "My rice crop in Kolkata West Bengal has brown spots on leaves with grey centers"
    When the agent processes the input
    Then it should identify the disease as Brown Spot
    And return structured diagnosis report
    And show severity level with color indicator

  Scenario: Farmer uploads crop photo
    Given a farmer uploads an image of a diseased crop
    And types a description of symptoms
    When the agent processes both image and text together
    Then it should use visual context for better diagnosis
    And return more accurate disease identification

  Scenario: Voice input in Hindi
    Given a farmer clicks the microphone button
    And selects Hindi language
    And speaks their crop problem in Hindi
    When speech is converted to text
    Then the text appears in the input box automatically
    And diagnosis works normally with Hindi input

  Scenario: Export diagnosis as PDF
    Given a diagnosis has been completed successfully
    When the farmer clicks Download Report button
    Then a PDF is generated with disease name, cause, action steps and prevention
    And PDF includes Kisan helpline number 1800-180-1551

  Scenario: View diagnosis history
    Given multiple diagnoses have been completed
    When the farmer views the history section
    Then last 5 diagnoses are shown with crop name and timestamp
    And each history item is clickable to view full details

  Scenario: Hindi translation of results
    Given a diagnosis result is shown in English
    When the farmer clicks Show in Hindi button
    Then the full diagnosis is translated to Hindi by Gemini API
    And all sections including cause and action steps appear in Hindi

  Scenario: Weather context affects diagnosis
    Given a farmer submits a crop problem with location
    When the agent fetches real time weather for that location
    Then it displays current temperature and humidity
    And adds a note if weather conditions favor disease spreading

  Scenario: Agent handles unknown crop
    Given a farmer describes symptoms for an unrecognized crop
    When the agent cannot find a confident match
    Then it asks one clarifying question
    And does not return empty or incorrect output
