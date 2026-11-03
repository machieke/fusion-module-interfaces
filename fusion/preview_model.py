"""Preview boundary hooks on the existing application ModelAdoption lifecycle."""
import time
from . import preview_model_contracts as c
from .contracts import canonical, digest, require
from .neoclaw_model import ModelAdoption
from .preview_model_binding import Client, configuration, contracts
from .preview_recorded_model import disclosure


def settings(app):
    cfg, chosen, frozen = configuration(app.config['model_config'])
    require((cfg['principal'],cfg['scope'],cfg['session']) ==
            (app.binding['principal'],app.preview_config['scope'],app.config['session_id']), 'UNAUTHORIZED')
    require('model_fixture' not in app.config and 'session_config' in app.config, 'UNSUPPORTED_PROFILE')
    require(1 <= app.config['turn_limit'] <= contracts(cfg).MAX_SESSION_CALLS, 'OVERLOADED')
    return cfg, chosen, frozen


class PreviewModel(ModelAdoption):
    def __init__(self, app):
        client=Client(app.config['model_config'])
        super().__init__(app, contracts=client.contracts, client=client)

    def current(self):
        cfg, chosen, frozen = settings(self.app)
        require(frozen == self.app.binding['model'], 'CONFLICT')
        self.app.preview.authorize('model.disclose')
        return cfg, chosen

    def source(self): return self.app.preview.input.model_source()

    def context_view(self):
        return digest(canonical(dict(task=self.app.preview.context_text(), source=self.source(),
            history=self.app.preview.history.context() if self.app.preview.history else None,
            catalogue=self.app.preview.catalogue.identity)))

    def parts(self, raw, cfg):
        require(type(raw) is str and raw.count(':-:-:-:') == 1)
        return dict(user=raw.split(':-:-:-:', 1)[1].strip())

    def model_identity(self, cfg):
        selected=contracts(cfg)
        limits=selected.LIMITS if selected is c else selected.limits(cfg['profile'])
        return dict(profile=cfg['profile'],model=selected.MODEL,model_digest=selected.MODEL_DIGEST,
                    transform=selected.TRANSFORM,limits=limits)

    def local_authority(self, accepted):
        cfg, _ = self.current()
        disclosure(accepted, cfg['disclosure'])
        source = self.source()
        require((accepted['source_id'],accepted['deadline_ms']) ==
                (source['message_id'],source['deadline_ms']), 'CONFLICT')
        # Input and source scope were accepted by the authenticated inbox;
        # provider policy independently authorizes execution/disclosure.
        expected = str(['HUMAN-MSG:', source['text'].replace('"','_quote_').replace("'",'_apostrophe_')])
        require(self.parts(accepted['native_prompt'], cfg)['user'] == expected, 'CONFLICT')
        return cfg

    def authorize_commands(self, cfg, slot, commands):
        origin=self.app.preview.input.source().get('task_origin')
        if origin is not None:
            expected=[['query',origin['record']['query']]] if origin['record']['kind']=='task' else [['task-context']]
            require(commands==expected,'UNAUTHORIZED')
        self.app.preview.catalogue.admit(commands, self.app.preview.authority(),
            self.app.binding['principal'], time.time_ns()//1_000_000)

    def complete(self, prompt):
        value=super().complete(prompt)
        if self.app.preview.history:self.app.preview.history.model()
        return value

    def invoke(self, operation, accepted):
        if operation == 'complete': self.app.preview.input.execution_permit()
        return super().invoke(operation, accepted)
