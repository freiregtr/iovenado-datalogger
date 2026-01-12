#!/usr/bin/env python3
"""
Simple Bluetooth agent with fixed PIN for automatic pairing.
This agent always responds with PIN "0000" for pairing requests.
"""

import sys
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

SERVICE_NAME = "org.bluez"
AGENT_INTERFACE = "org.bluez.Agent1"
AGENT_PATH = "/test/agent"

# Fixed PIN for pairing
FIXED_PIN = "0000"


class Agent(dbus.service.Object):
    """Bluetooth pairing agent with fixed PIN"""

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Release(self):
        print(f"[Agent] Release")

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print(f"[Agent] AuthorizeService: {device}, {uuid}")
        return

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print(f"[Agent] RequestPinCode: {device} -> returning '{FIXED_PIN}'")
        return FIXED_PIN

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print(f"[Agent] RequestPasskey: {device} -> returning {FIXED_PIN}")
        return dbus.UInt32(int(FIXED_PIN))

    @dbus.service.method(AGENT_INTERFACE, in_signature="ou", out_signature="")
    def DisplayPasskey(self, device, passkey):
        print(f"[Agent] DisplayPasskey: {device}, {passkey:06d}")

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        print(f"[Agent] DisplayPinCode: {device}, {pincode}")

    @dbus.service.method(AGENT_INTERFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print(f"[Agent] RequestConfirmation: {device}, {passkey:06d} -> auto-accepting")
        return

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print(f"[Agent] RequestAuthorization: {device} -> auto-accepting")
        return

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Cancel(self):
        print(f"[Agent] Cancel")


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()
    agent = Agent(bus, AGENT_PATH)

    manager = dbus.Interface(
        bus.get_object(SERVICE_NAME, "/org/bluez"),
        "org.bluez.AgentManager1"
    )

    manager.RegisterAgent(AGENT_PATH, "KeyboardDisplay")
    manager.RequestDefaultAgent(AGENT_PATH)

    print(f"[Agent] Bluetooth agent registered with fixed PIN: {FIXED_PIN}")
    print(f"[Agent] Waiting for pairing requests...")

    mainloop = GLib.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()
