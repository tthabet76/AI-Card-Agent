print("--- Starting Selenium Diagnostic Test ---")
try:
    from selenium.webdriver.support import expected_conditions as EC

    # This is the function that is causing the error in our main script.
    # We are checking what Python thinks its type is.
    function_to_test = EC.presence_of_element_located

    print(f"The type of the function is: {type(function_to_test)}")

    # It should be a <class 'function'>. If it's something else, we've found the problem.

except Exception as e:
    print(f"An error occurred during the import or test: {e}")

print("--- Diagnostic Test Finished ---")