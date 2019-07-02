#!/bin/python
import subprocess
import time
# import iptc.easy
import os
import re


def old_patch():
    iptables_config = subprocess.run(
        ["iptables-save"], capture_output=True).stdout.decode("utf-8")
    if iptables_config.find("LOCAL") != -1:
        iptables_config = iptables_config.replace("LOCAL", "BROADCAST")
        subprocess.run(["iptables-restore"],
                       input=iptables_config.encode("utf-8"))
        print("Patched")

'''
def patch(port_list):
    chain_out = iptc.Chain(iptc.Table(iptc.Table.NAT), "OUTPUT")
    chain_prerouting = iptc.Chain(iptc.Table(iptc.Table.NAT), "PREROUTING")
    for rule in chain_out.rules:
        if rule.matches[0].parameters["dport"] in port_list:
            print(chain_out.rules.index(rule))
            print(rule.matches[0].parameters["dport"])
            rule_dict = iptc.easy.decode_iptc_rule(rule)
            rule_dict["addrtype"]["dst-type"] = "BROADCAST"
            new_rule = iptc.easy.encode_iptc_rule(rule_dict)
            chain_out.replace_rule(new_rule, chain_out.rules.index(rule))
            print(f"OUTPUT {rule_dict['tcp']['dport']} Patched.")
    for rule in chain_prerouting.rules:
        if rule.matches[0].parameters["dport"] in port_list:
            rule_dict = iptc.easy.decode_iptc_rule(rule)
            rule_dict["addrtype"]["dst-type"] = "BROADCAST"
            new_rule = iptc.easy.encode_iptc_rule(rule_dict)
            chain_prerouting.replace_rule(new_rule, chain_prerouting.rules.index(rule))
            print(f"PREROUTING {rule_dict['tcp']['dport']} Patched.")

def get_port_list():
    port = []
    for machine in os.listdir("containers/machines"):
        with open(f"/etc/systemd/nspawn/{machine}.nspawn") as f:
            nspawn_content = f.read()
        port.append(re.findall("(?<=Port=)\d*", nspawn_content)[0])  # noqa
    return port


port_list = get_port_list()
'''
while True:
    old_patch()
    time.sleep(5)
