#!/usr/bin/env python

import sys
from pathlib import Path
import shutil
import argparse
import errno
import subprocess
import yaml

PROJECT_ROOT = Path("/code")
BUILD_DIR = PROJECT_ROOT / "build"

def in_docker():
    """ Returns: True if runnning in a docker container, else False """
    try:
        with open("/proc/1/cgroup", "rt") as ifh:
            return "docker" in ifh.read()
    except:
        return False

def run(cmd, cwd=PROJECT_ROOT, check_exit=True):
    try:
        exit_code = subprocess.call(cmd, cwd=cwd)

        if check_exit and exit_code != 0:
            print(f"{' '.join(cmd)} exited with non-zero {exit_code}")
    except OSError as e:
        if e.errno == errno.ENOENT:
            print(f"Command {cmd[0]} not found")
            raise e
        else:
            raise e

def cmake(flags=None):
    
    # Delete entire build directory if it exists
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    # Create new build directory
    BUILD_DIR.mkdir()

    # Create cmake command
    cmd = ["cmake", "-GNinja"]
    if flags is not None:
        cmd += flags
    cmd += [".."]

    run(cmd, cwd=BUILD_DIR)

def build(flags=None):

    if not BUILD_DIR.exists():
        raise FileNotFoundError("Could not find build directory to run build")

    cmd = ["ninja"]
    if flags is not None:
        cmd += flags

    run(cmd, cwd=BUILD_DIR)

def test(flags=None):

    if not BUILD_DIR.exists():
        raise FileNotFoundError("Could not find build directory to run tests")

    cmd = ["ninja", "check"]
    if flags is not None:
        cmd += flags

    run(cmd, cwd=BUILD_DIR)

def format():
    format_hdl()
    format_cpp_cmake()

def format_hdl():
    """ Format SystemVerilog and Verilog files """

    # Use --inplace flag to overwrite existing files
    cmd = ["verible-verilog-format", "--inplace"]

    # Add options from .verible-verilog-format.yaml if specified
    verible_verilog_format_yaml = PROJECT_ROOT / ".verible-verilog-format.yaml"
    yaml_data = None
    if verible_verilog_format_yaml.exists():
        with open(verible_verilog_format_yaml, "r") as f:
            yaml_data = yaml.safe_load(f.read())

    format_args = []
    for k, v in yaml_data.items():
        format_args.append(f"--{k}={v}")

    cmd += format_args

    # Add all SystemVerilog or Verilog files in any project directory
    hdl_search_patterns = ["**/*.sv", "**/*.v"]
    hdl_files = []
    for sp in hdl_search_patterns:
        hdl_files += PROJECT_ROOT.glob(sp)
    cmd += [str(f) for f in hdl_files]

    run(cmd)

def format_cpp_cmake():
    """ Format C++ and cmake files """
    cmake()

    cmd = ["ninja", "fix-format"]
    run(cmd, cwd=BUILD_DIR)

if __name__ == "__main__":
    if not in_docker():
        raise OSError("Not in a docker container. This script must be run from within a docker container. See README.md for instructions.")
    else:

        # Resolve project root directory before proceeding
        if not PROJECT_ROOT.is_dir():
            raise FileNotFoundError(f"Cannot find project root directory: {PROJECT_ROOT}")

        parser = argparse.ArgumentParser()
        arg_list = ["--skip-build", "--skip-test", "--skip-format"]
        for arg in arg_list:
            parser.add_argument(arg, action="store_true")
        args = parser.parse_args()

        if not args.skip_format:
            print("Formatting...")
            format()

        if not args.skip_build:
            print("Building...")
            cmake()
            build()

            if not args.skip_test:
                print("Testing...")
                test()
        