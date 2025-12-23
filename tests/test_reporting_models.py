from tests.reporting import validate_event, validate_cards


def test_event_validation_and_cards():
    evt = {"ts":"t","test":"t1","event":"PROMPT","payload":{"prompt":"hi"}}
    ve = validate_event(evt)
    assert ve is not None

    cards = [{"test":"t1","prompt":"hi","answer":"ok","parsed_tool":None}, {"test":"t2","prompt":1,"answer":"no"}]
    vcards = validate_cards(cards)
    assert len(vcards) == 1
