"""Ryu/os-ken controller that installs deterministic static routes."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from ryu.base import app_manager
    from ryu.controller import ofp_event
    from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
    from ryu.lib.packet import arp, ethernet, packet
    from ryu.ofproto import ofproto_v1_3
except ImportError:  # pragma: no cover - exercised in Linux SDN environments using os-ken
    from os_ken.base import app_manager
    from os_ken.controller import ofp_event
    from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
    from os_ken.lib.packet import arp, ethernet, packet
    from os_ken.ofproto import ofproto_v1_3


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "static_routes.json"
CONTROLLER_APP_BASE = getattr(app_manager, "RyuApp", getattr(app_manager, "OSKenApp"))


class StaticRoutingController(CONTROLLER_APP_BASE):
    """Install static forwarding rules on switch connect."""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            self.route_config = json.load(handle)
        self.flow_map = self.route_config["flows"]
        self.hosts = self.route_config["hosts"]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self._install_table_miss(datapath, parser, ofproto)
        self._install_static_flows(datapath, parser, ofproto)
        self.logger.info("Installed static routes on switch dpid=%s", datapath.id)

    def _install_table_miss(self, datapath, parser, ofproto):
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(datapath, priority=0, match=match, actions=actions)

    def _install_static_flows(self, datapath, parser, ofproto):
        dpid_key = str(datapath.id)
        if dpid_key not in self.flow_map:
            self.logger.warning("No static flow plan found for dpid=%s", datapath.id)
            return

        # ARP is flooded so hosts can resolve each other before static L2 forwarding takes over.
        arp_match = parser.OFPMatch(eth_type=0x0806)
        arp_actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self._add_flow(datapath, priority=50, match=arp_match, actions=arp_actions)

        for dst_mac, out_port in self.flow_map[dpid_key].items():
            match = parser.OFPMatch(eth_dst=dst_mac)
            actions = [parser.OFPActionOutput(out_port)]
            self._add_flow(datapath, priority=100, match=match, actions=actions)

    def _add_flow(self, datapath, priority, match, actions):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        request = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=instructions,
        )
        datapath.send_msg(request)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None:
            return

        if pkt.get_protocol(arp.arp):
            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=msg.buffer_id,
                in_port=msg.match["in_port"],
                actions=actions,
                data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None,
            )
            datapath.send_msg(out)
