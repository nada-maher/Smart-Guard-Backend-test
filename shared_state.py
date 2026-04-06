# backend/shared_state.py



from collections import defaultdict

import time



# متغير مشترك لتخزين آخر# shared_state.py

latest_pred = None

camera_enabled = True # Default to True

stop_requested = False  # Flag to prevent auto-reopen on logout



# MULTI-TENANT ORGANIZATION ISOLATION
LOGIN_DELAY = 300  # 5 minutes login delay (adjust as needed)
ALERT_COOLDOWN = 90  # 90 seconds alert cooldown (adjust as needed)

# Global current organization (synced between main and stream processor)
current_organization = "Smart Guard"

class OrgState:

    """Per-organization state management"""

    def __init__(self):

        self.login_time = 0

        self.last_alerts = {}  # {camera_id: timestamp}

        self.stream_active = False

        self.camera_enabled = True

        self.detection_active = False

        self.stop_requested = False  # Flag to prevent auto-reopen on logout



# Global organization states dictionary

org_states = defaultdict(OrgState)



def get_org_state(org_name):

    """Get or create organization state"""

    state = org_states[org_name]

    print(f" [DEBUG] get_org_state('{org_name}') → {id(state)} with login_time={state.login_time}")

    return state



def set_org_camera_status(org_name, enabled):

    """Set camera status for specific organization"""

    org_state = get_org_state(org_name)

    org_state.camera_enabled = enabled

    print(f" [DEBUG] set_org_camera_status('{org_name}', {enabled})")



def get_org_camera_status(org_name):

    """Get camera status for specific organization"""

    org_state = get_org_state(org_name)

    return org_state.camera_enabled



def request_camera_stop(org_name):

    """Request camera stop and prevent auto-reopen"""

    org_state = get_org_state(org_name)

    org_state.stop_requested = True

    org_state.camera_enabled = False

    print(f" [DEBUG] Camera stop requested for {org_name} - prevent auto-reopen")



def clear_camera_stop_request(org_name):

    """Clear camera stop request (allow normal operation)"""

    org_state = get_org_state(org_name)

    org_state.stop_requested = False

    print(f" [DEBUG] Camera stop request cleared for {org_name} - normal operation resumed")



def is_camera_stop_requested(org_name):

    """Check if camera stop is requested"""

    org_state = get_org_state(org_name)

    return org_state.stop_requested



loop = None # Global event loop for WebSockets

