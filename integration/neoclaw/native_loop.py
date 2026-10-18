"""Supported controlled native-loop launcher; checked additive overlay, no upstream edits.

Run `python -m integration.neoclaw.native_loop APPLICATION.json`.
Only composition changes placement. Original default/live startup is not this recipe.
"""
import argparse
import json
import os
from pathlib import Path

from fusion.adapters.neoclaw_nal import NativeTruthDeduction
from fusion.contracts import canonical, digest, require
from fusion import neoclaw_contracts as c
from fusion import neoclaw_operations as ops
from .startup_overlay import adapted_loop, adapted_skill, adapted_channels, replace_once

ROOT = Path(__file__).resolve().parents[2]


def prepare(config_file):
    config_file = Path(config_file).resolve()
    config = json.loads(config_file.read_text())
    require(config['composition'] in ('controlled-native-loop/1', ops.APPLICATION), 'UNSUPPORTED_PROFILE')
    runtime = NativeTruthDeduction(config['runtime']).runtime
    omega, petta = Path(runtime['mettaclaw']), Path(runtime['petta'])
    source_files = ('run.metta', 'lib_mettaclaw.metta', 'src/loop.metta', 'src/channels.metta',
                    'src/memory.metta', 'src/skills.metta', 'src/helper.py', 'src/utils.metta', 'src/skills.pl', 'lib_nal.metta')
    for file in source_files:
        require(digest((omega/file).read_bytes()) == c.PINS['sources']['mettaclaw']['files'][file], 'UNSUPPORTED_PROFILE')
    directory = Path(config['workdir']).resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    (directory/'repos/mettaclaw/memory').mkdir(parents=True, exist_ok=True)
    skills, loop = directory/'skills.metta', directory/'loop.metta'
    skills.write_text(adapted_skill((omega/'src/skills.metta').read_text()))
    loop.write_text(adapted_loop((omega/'src/loop.metta').read_text()))
    channels = omega/'src/channels.metta'
    if config['composition'] == ops.APPLICATION:
        channels = directory/'channels.metta'
        channels.write_text(adapted_channels((omega/'src/channels.metta').read_text()))
    llm = directory/'lib_llm.metta'
    llm.write_text(replace_once((petta/'lib/lib_llm.metta').read_text(),
        '!(change-state! &openai_client (py-call (openai.OpenAI)))',
        '; controlled composition: hosted OpenAI client is not initialized'))
    fixtures = ROOT/'integration/neoclaw/controlled'
    imports = [llm, omega/'src/helper.py', omega/'src/utils.metta', skills, omega/'lib_nal.metta',
               fixtures/'lib_llm_ext.py', fixtures/'irc.py', channels, fixtures/'memory.metta',
               ROOT/'integration/neoclaw/neoclaw_bridge.py', ROOT/'integration/neoclaw/loop_bridge.py', loop]
    lines = ['!(import! &self (library lib_import))', '!(import! &self (library lib_patrick))']
    lines += ['!(import! &self '+json.dumps(str(p))+')' for p in imports]
    lines += ['!(if (py-call (loop_bridge.start)) (mettaclaw) S01-BOUNDED-STOP)']
    entry = directory/'start.metta'; entry.write_text('\n'.join(lines)+'\n')
    manifest = dict(composition=config['composition'], source_commit=c.PINS['sources']['mettaclaw']['commit'],
                    source_hashes={f:digest((omega/f).read_bytes()) for f in source_files},
                    overlay_hashes={p.name:digest(p.read_bytes()) for p in (entry, skills, loop, llm)},
                    fixture_hashes={p.name:digest(p.read_bytes()) for p in fixtures.iterdir() if p.is_file()},
                    substitutions=['PeTTa lib_llm native string helpers retained; hosted OpenAI client initialization suppressed',
                                   'external model: scripted responses, observed context assertions',
                                   'IRC Python boundary: no sockets, empty ingress, send rejects',
                                   'memory facade: init maxFeedback=50000, empty recall/history, no-op history append',
                                   'media/embeddings/Chroma/Mattermost/web search: not imported or initialized',
                                   'generated empty persistent space exported by native loop; no user store import'],
                    entrypoint='mettaclaw', bounded_turns=config['turn_limit'])
    (directory/'startup.json').write_bytes(canonical(manifest))
    if config['composition'] == ops.APPLICATION:
        manifest['overlay_hashes']['channels.metta'] = digest(channels.read_bytes())
        manifest['substitutions'][4] = 'media/embeddings/Chroma/Mattermost not initialized; search uses closed S02 port; SDK executes only at provider'
        (directory/'startup.json').write_bytes(canonical(manifest))
    env = {k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL','TMPDIR')}
    env.update(runtime['environment'])
    env['NEOCLAW_S01_APPLICATION'] = str(config_file)
    env['NEOCLAW_S01_CALLER'] = str(Path(config['caller_config']).resolve())
    goal = "asserta(library_path('"+str(omega).replace("'", "''")+"'))"
    args = [runtime['swipl'], '-q', '-s', str(petta/'src/main.pl'), '-g', goal, '--', str(entry), '--silent',
            'maxNewInputLoops=128', 'sleepInterval=0']
    if config.get('denied_paths'):
        args = ['bwrap', '--die-with-parent', '--ro-bind', '/', '/', '--bind', '/tmp', '/tmp',
                '--proc', '/proc', '--dev', '/dev',
                *[v for p in config['denied_paths'] for v in ('--tmpfs', str(Path(p).resolve()))], '--', *args]
    return args, env, directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config')
    args = parser.parse_args()
    command, environment, directory = prepare(args.config)
    os.chdir(directory)
    os.execvpe(command[0], command, environment)


if __name__ == '__main__': main()
