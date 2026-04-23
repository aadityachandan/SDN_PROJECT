"""Mininet topology for a three-switch static-routing SDN lab."""

from __future__ import annotations

import argparse
import os
import socket

from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController


def controller_is_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True when the configured controller socket accepts a connection."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def build_network(controller_ip: str, controller_port: int):
    net = Mininet(controller=RemoteController, switch=OVSSwitch, link=TCLink, autoSetMacs=False)

    controller = net.addController(
        "c0",
        controller=RemoteController,
        ip=controller_ip,
        port=controller_port,
    )

    s1 = net.addSwitch("s1", dpid="0000000000000001", protocols="OpenFlow13")
    s2 = net.addSwitch("s2", dpid="0000000000000002", protocols="OpenFlow13")
    s3 = net.addSwitch("s3", dpid="0000000000000003", protocols="OpenFlow13")

    h1 = net.addHost("h1", ip="10.0.0.1/24", mac="00:00:00:00:00:01")
    h2 = net.addHost("h2", ip="10.0.0.2/24", mac="00:00:00:00:00:02")
    h3 = net.addHost("h3", ip="10.0.0.3/24", mac="00:00:00:00:00:03")
    h4 = net.addHost("h4", ip="10.0.0.4/24", mac="00:00:00:00:00:04")

    net.addLink(h1, s1, port2=1)
    net.addLink(h2, s1, port2=2)
    net.addLink(s1, s2, port1=3, port2=1)
    net.addLink(s2, s3, port1=2, port2=3)
    net.addLink(h3, s3, port2=1)
    net.addLink(h4, s3, port2=2)

    net.build()
    controller.start()
    s1.start([controller])
    s2.start([controller])
    s3.start([controller])
    return net


def parse_args():
    parser = argparse.ArgumentParser(description="Launch the static-routing Mininet topology.")
    parser.add_argument(
        "--controller-ip",
        default=os.environ.get("SDN_CONTROLLER_IP", "127.0.0.1"),
        help="Remote controller IP address (default: %(default)s or SDN_CONTROLLER_IP).",
    )
    parser.add_argument(
        "--controller-port",
        type=int,
        default=int(os.environ.get("SDN_CONTROLLER_PORT", "6633")),
        help="Remote controller port (default: %(default)s or SDN_CONTROLLER_PORT).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not controller_is_reachable(args.controller_ip, args.controller_port):
        print(
            "\nWarning: remote controller is not reachable at "
            f"{args.controller_ip}:{args.controller_port}."
        )
        print("Start the controller first, for example:")
        print("  ryu-manager src/controller/static_routing_controller.py")
        print(
            "Or relaunch the topology with a different endpoint, for example:"
        )
        print(
            "  sudo python3 src/topology/static_topology.py "
            "--controller-ip 127.0.0.1 --controller-port 6653\n"
        )

    net = build_network(args.controller_ip, args.controller_port)
    print("\nStatic routing topology is up.")
    print(f"Controller target: {args.controller_ip}:{args.controller_port}")
    print("Recommended validation commands:")
    print("  pingall")
    print("  h1 ping -c 3 h3")
    print("  h2 ping -c 3 h4")
    print("  sh ovs-ofctl -O OpenFlow13 dump-flows s1")
    print("  sh ovs-ofctl -O OpenFlow13 dump-flows s2")
    print("  sh ovs-ofctl -O OpenFlow13 dump-flows s3\n")
    CLI(net)
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    main()
