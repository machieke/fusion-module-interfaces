"""Installed dispatch to existing bounded operator tools; no background work."""
import argparse,importlib,sys

COMMANDS={
    'services':'integration.single_node.sustained_cli',
    'values':'integration.single_node.pilot_values',
    'browser':'integration.single_node.pilot_browser_cli',
    'backup':'integration.single_node.pilot_backup',
    'dependencies':'integration.single_node.pilot_dependency_operator',
    'upgrade-copy':'integration.single_node.pilot_upgrade',
    'handover':'integration.single_node.pilot_handover_operator',
    'handover-values':'examples.pilot_handover_values',
    'verify-evidence':'integration.single_node.pilot_evidence',
    'verify-artifacts':'integration.single_node.reference_artifacts',
    'placement':'integration.single_node.placement',
    'qualify-endurance':'examples.pilot_endurance',
    'qualify-workflow':'examples.pilot_workflows',
    'qualify-recipe':'examples.pilot_recipe_qualification',
    'qualify-handover':'examples.pilot_handover',
    'qualify-browser':'examples.pilot_browser_qualification',
    'qualify-faults':'examples.pilot_faults',
    'qualify-go-provider':'examples.pilot_go_provider',
    'qualify-recipe-chain':'examples.pilot_recipe_chain',
    'qualify-workflow-restore':'examples.pilot_workflow_restore',
    'observe-runtime':'examples.pilot_observations',
}


def main():
    parser=argparse.ArgumentParser(description=__doc__,epilog='Each command retains its own explicit scope, authority and finite limits. No command authorizes live generation.')
    parser.add_argument('command',choices=COMMANDS);parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args();original=sys.argv
    try:
        sys.argv=['fusion-pilot '+args.command,*args.arguments]
        importlib.import_module(COMMANDS[args.command]).main()
    finally:sys.argv=original


if __name__=='__main__':main()
