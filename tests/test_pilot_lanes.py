import unittest
from fusion.service_lanes import Lanes,PROFILE,LIMITS,classify
from fusion.contracts import ContractError

class LanesTests(unittest.TestCase):
    def test_normal_pressure_preserves_read_and_control_slots(self):
        lanes=Lanes(dict(profile=PROFILE,limits=LIMITS));held=[]
        for actor in ('A','A','B','B'):held.append(lanes.enter('normal',actor))
        with self.assertRaisesRegex(ContractError,'OVERLOADED'):lanes.enter('normal','C')
        for name in ('observation','maintenance'):
            with lanes.admit('/preview/session',dict(operation='observe' if name=='observation' else 'cancel'),'A'):pass
        for key in held:lanes.leave(key)
        self.assertEqual(lanes.observe()['active'],dict(normal=0,maintenance=0,observation=0))
    def test_one_actor_cannot_fill_all_normal_or_read_slots(self):
        lanes=Lanes(dict(profile=PROFILE,limits=LIMITS))
        for name in ('normal','observation'):
            keys=[lanes.enter(name,'A') for _ in range(2)]
            with self.assertRaisesRegex(ContractError,'OVERLOADED'):lanes.enter(name,'A')
            key=lanes.enter(name,'B');lanes.leave(key)
            for key in keys:lanes.leave(key)
    def test_classification_cannot_create_effect_authority_or_implicit_retry(self):
        self.assertEqual(classify('/arbitrary',{'operation':'observe'}),'normal')
        self.assertEqual(classify('/preview/session',{'operation':'submit'}),'normal')
        lanes=Lanes(dict(profile=PROFILE,limits=LIMITS))
        with self.assertRaises(RuntimeError):
            with lanes.admit('/preview/session',{'operation':'submit'},'A'):raise RuntimeError('lost response')
        self.assertEqual(lanes.observe()['retries'],0)
        self.assertEqual(lanes.observe()['active']['normal'],0)
