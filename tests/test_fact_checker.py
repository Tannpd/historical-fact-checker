import pytest
import json

def test_initial_state(direct_deploy):
    # Deploy contract and check initial count is 0
    contract = direct_deploy("contracts/fact_checker.py", sdk_version="v0.2.16")
    assert contract.get_total_records() == 0

def test_input_validation(direct_deploy, direct_vm):
    contract = direct_deploy("contracts/fact_checker.py", sdk_version="v0.2.16")
    
    # Test empty claim
    with pytest.raises(Exception) as excinfo:
        contract.verify_claim("", "https://en.wikipedia.org/wiki/Battle_of_Bach_Dang_(938)", "https://example.com")
    assert "claim must not be empty" in str(excinfo.value)
    
    # Test invalid url1
    with pytest.raises(Exception) as excinfo:
        contract.verify_claim("A historical claim", "ftp://example.com", "https://example.com")
    assert "url1 must be a valid HTTP/HTTPS URL" in str(excinfo.value)
    
    # Test invalid url2
    with pytest.raises(Exception) as excinfo:
        contract.verify_claim("A historical claim", "https://example.com", "invalid-url")
    assert "url2 must be a valid HTTP/HTTPS URL" in str(excinfo.value)

def test_verify_claim_happy_path(direct_deploy, direct_vm):
    contract = direct_deploy("contracts/fact_checker.py", sdk_version="v0.2.16")
    
    # Mock web page rendering
    direct_vm.mock_web(
        r".*wiki.*938.*",
        {"method": "GET", "status": 200, "body": "The Battle of Bach Dang River occurred in 938 AD. Ngo Quyen defeated the Southern Han army."}
    )
    direct_vm.mock_web(
        r".*example.*",
        {"method": "GET", "status": 200, "body": "Historical events registry lists Ngo Quyen defeating Han in Bach Dang in the year 938."}
    )
    
    # Mock LLM verdict
    direct_vm.mock_llm(
        r".*",
        '{"verdict": "TRUE", "confidence": 98, "reason": "Both reference pages confirm that the Battle of Bach Dang occurred in 938 AD led by Ngo Quyen."}'
    )
    
    # Execute fact checking
    contract.verify_claim(
        claim="The Battle of Bach Dang occurred in 938 AD.",
        url1="https://en.wikipedia.org/wiki/Battle_of_Bach_Dang_(938)",
        url2="https://example.com/bachdang"
    )
    
    assert contract.get_total_records() == 1
    
    # Retrieve and parse record
    record_json = contract.get_record("0")
    record = json.loads(record_json)
    
    assert record["id"] == "0"
    assert record["claim"] == "The Battle of Bach Dang occurred in 938 AD."
    assert record["url1"] == "https://en.wikipedia.org/wiki/Battle_of_Bach_Dang_(938)"
    assert record["url2"] == "https://example.com/bachdang"
    assert record["verdict"] == "TRUE"
    assert record["confidence"] == 98
    assert record["reason"] == "Both reference pages confirm that the Battle of Bach Dang occurred in 938 AD led by Ngo Quyen."
