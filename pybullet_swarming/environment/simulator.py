import copy
import numpy as np

from pybullet_swarming.environment.environment import *
from pybullet_swarming.utility.shebangs import  *
from pybullet_swarming.flier.swarm_controller import *

class Simulator():
    """
    Class wrapper around `environment` to be concise with the swarm controller
    Control is done using linear velocity setpoints and yawrate:
        vx, vy, vz, vr
    States is full linear position and yaw
        x, y, z, r
    """
    def __init__(self, start_pos, start_orn):

        # instantiate the digital twin
        self.env = Aviary(start_pos=start_pos, start_orn=start_orn, render=True)
        self.set_pos_control(True)
        self.env.set_go([0] * self.env.num_drones)

        # keep track of runtime
        self.steps = 0

        # texturing
        tex_id = self.env.loadTexture('/models/diamond4.png')
        # self.env.changeVisualShape(self.env.planeId, -1, textureUniqueId=tex_id)

        for drone in self.env.drones:
            self.env.changeVisualShape(drone.Id, -1, textureUniqueId=tex_id)


    def reshuffle(self, new_pos, new_orn):
        """
        reshuffle the drones given a new start_pos such that all drones map to the new start_pos cleanly
        """
        # if start pos is given, reassign to get drones to their positions automatically
        assert new_pos.shape == new_orn.shape, 'start_pos must have same shape as start_orn'
        assert len(new_pos) == self.num_drones, 'must have same number of drones as number of drones'
        assert new_pos[0].shape[0] == 3, 'start pos must have only xyz, start orn must have only pqr'

        # compute cost matrix
        cost = abs(np.expand_dims(self.states[:, :3], axis=0) - np.expand_dims(new_pos, axis=1))
        cost = np.sum(cost, axis=-1)

        # compute optimal assignment using Hungarian algo
        _, reassignment = linear_sum_assignment(cost)
        self.env.drones = [self.env.drones[i] for i in reassignment]

        # send setpoints
        setpoints = np.concatenate((new_pos, np.expand_dims(new_orn[:, -1], axis=-1)), axis=-1)
        self.set_setpoints(setpoints)
        self.set_pos_control(True)

        cost = np.choose(reassignment, cost.T)
        return cost


    def set_setpoints(self, setpoints: np.ndarray):
        """
        setpoints is a num_drones x 4 array, where the 4 corresponds to x, y, z, r or vx, vy, vz, vr
        """
        # the setpoints in the digital twin has the last two dims flipped
        temp = copy.deepcopy(setpoints[:, -2])
        setpoints[:, -2] = copy.deepcopy(setpoints[:, -1])
        setpoints[:, -1] = temp
        self.env.set_setpoints(setpoints)


    def step(self):
        self.steps += 1
        self.env.step()


    def set_pos_control(self, setting):
        """sets entire swarm to fly using pos control"""
        self.env.set_mode(7 if setting else 6)


    def get_states(self):
        states = np.zeros((self.num_drones, 4))
        states[:, :-1] = copy.deepcopy(self.env.states[:, -1, :])
        states[:, -1] = copy.deepcopy(self.env.states[:, 1, -1])

        return states


    def sleep(self, seconds: float):
        for _ in range(int(seconds / self.env.period)):
            self.step()


    def go(self, settings):
        self.env.set_go(settings)


    @property
    def states(self):
        return self.get_states()


    @property
    def num_drones(self):
        return self.env.num_drones


    @property
    def elapsed_time(self):
        return self.env.period * self.steps
