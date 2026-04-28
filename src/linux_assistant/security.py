from __future__ import annotations

import re

from linux_assistant.schemas import CommandPlan, RiskLevel, SafetyAssessment


HIGH_RISK_PATTERNS: dict[str, str] = {
    r"\brm\s+-rf\s+/(\s|$)": "Deletes the filesystem root recursively.",
    r"\bmkfs(\.\w+)?\b": "Formats a filesystem.",
    r"\bdd\s+if=": "Performs raw disk copying.",
    r"\bshutdown\b": "Shuts down the system.",
    r"\breboot\b": "Reboots the system.",
    r"\bpoweroff\b": "Powers off the system.",
    r"\binit\s+0\b": "Stops the system.",
    r"\buserdel\b": "Deletes system users.",
    r"\bmount\b": "Changes mounted filesystems.",
    r"\bumount\b": "Unmounts filesystems.",
    r"\biptables\b": "Modifies firewall rules.",
    r"\bufw\b": "Modifies firewall rules.",
    r">\s*/etc/": "Writes directly into /etc configuration.",
    r"\bchmod\b.*\s/etc/": "Changes permissions under /etc.",
    r"\bchown\b.*\s/etc/": "Changes ownership under /etc.",
}

MODERATE_RISK_PATTERNS: dict[str, str] = {
    r"\bsudo\b": "Uses elevated privileges.",
    r"\brm\b": "Deletes files.",
    r"\bmv\b": "Moves or overwrites files.",
    r"\bcp\b": "Copies files and may overwrite existing files.",
    r"\bchmod\b": "Changes file permissions.",
    r"\bchown\b": "Changes file ownership.",
    r"\bsystemctl\b": "Modifies or inspects services.",
    r"\bapt(-get)?\b": "Installs or removes packages.",
    r"\byum\b": "Installs or removes packages.",
    r"\bdnf\b": "Installs or removes packages.",
    r"\bpip3?\s+install\b": "Installs Python packages.",
    r"\bcurl\b.*\|\s*(bash|sh)": "Executes downloaded remote content.",
}


class CommandSafetyChecker:
    def assess(self, plan: CommandPlan, allow_dangerous: bool) -> SafetyAssessment:
        if plan.action_type != plan.action_type.RUN_SHELL or not plan.command:
            return SafetyAssessment(
                allowed=True,
                dangerous=False,
                risk_level=plan.risk_level,
                reasons=list(plan.risk_reasons),
            )

        command = plan.command.strip()
        reasons = list(plan.risk_reasons)
        dangerous = False
        computed_risk = plan.risk_level

        for pattern, reason in HIGH_RISK_PATTERNS.items():
            if re.search(pattern, command):
                dangerous = True
                computed_risk = RiskLevel.HIGH
                reasons.append(reason)

        if computed_risk != RiskLevel.HIGH:
            for pattern, reason in MODERATE_RISK_PATTERNS.items():
                if re.search(pattern, command):
                    computed_risk = RiskLevel.MODERATE
                    reasons.append(reason)

        allowed = True
        if dangerous and not allow_dangerous:
            allowed = False
            reasons.append("Blocked by policy because dangerous commands are disabled.")

        return SafetyAssessment(
            allowed=allowed,
            dangerous=dangerous,
            risk_level=computed_risk,
            reasons=_deduplicate(reasons),
        )


def _deduplicate(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduplicated: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduplicated.append(value)
    return deduplicated
