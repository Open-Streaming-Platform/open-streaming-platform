import uuid
from classes import Sec

def test_new_guest():
    """
    Sec.Guest Unit Test
    """
    guestUUID = uuid.uuid4()
    guestIP = "127.0.0.1"
    guest_test = Sec.Guest(str(guestUUID), guestIP)
    assert guest_test.UUID == str(guestUUID)
    assert guest_test.last_active_ip == guestIP

