from scipy import stats
import numpy as np

class Distribution:
    def __init__(self, dist_type, params):
        self.type = dist_type
        self.params = params

    def get_distribution(self):
        if self.type == 'normal':
            return stats.norm(loc=self.params['mean'], scale=self.params['std'])
        elif self.type == 'exponential':
            return stats.expon(scale=1/self.params['lambda'])