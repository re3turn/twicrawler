#!/usr/bin/python3

import os
import sys
import termcolor


class Env:
    @staticmethod
    def get_environment(env_name, default=None, required=False):
        env = os.environ.get(env_name, default)
        if required and (default is None) and (env is None):
            sys.exit(termcolor.colored(f'Error: Please set environment "{env_name}"', 'red'))

        return env
