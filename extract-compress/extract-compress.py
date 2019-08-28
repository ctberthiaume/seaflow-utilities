#!/usr/bin/env python3
# Extract SeaFlow raw data from day-of-year zip files then gzip EVT files.
#
# To use this script, enter a list of cruise names to process in a file in the
# current working directory and pass it to this script as a command-line
# argument. Cruises can be commented out with an initial "#". One cruise per
# line. Also in the current  working directory there should be corresponding
# cruise folders containing one zip file per day-of-year folder, each of which
# expands to a day-of-year folder containing uncompressed EVT files.
#
# This script will unzip each zip file, erase any metadata files/dirs such as
# "__MACOSX" or .DS_Store, erase the zip file, then gzip compress EVT files
# with pigz. Once this process is completed the cruise folder is ready for
# upload to S3.
import argparse
import glob
import os
import shutil
import subprocess
import sys


def remove_metadata_files():
    print("Cleaning up __MACOSX or .DS_Store")
    # Files in cruise root
    toremove = glob.glob("__MACOSX")
    toremove.extend(glob.glob(".DS_Store"))
    # Files in any day-of-year subdirectory
    toremove = glob.glob("*/__MACOSX")
    toremove.extend(glob.glob("*/.DS_Store"))
    for f in toremove:
        print(f"Removing {f}")
        if os.path.isdir(f):
            shutil.rmtree(f)
        elif os.path.isfile(f):
            os.remove(f)
        else:
            raise OSError(f"Could not determine type of {f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process HOT SeaFlow zip files')
    parser.add_argument('cruisefile', type=str, help='List of cruises to process')
    args = parser.parse_args()

    with open(args.cruisefile, mode="r", encoding="utf8") as fh:
        cruises = [l.rstrip() for l in fh.readlines() if not l.startswith("#")]

    for c in cruises:
        try:
            os.mkdir(c)
        except FileExistsError:
            pass

        try:
            os.chdir(c)
            print(f"Entering {c}")
        except OSError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

        zips = glob.glob("*.zip")
        for z in zips:
            # Extract a day-of-year zip file
            try:
                print(f"Extracting {z}")
                subprocess.check_call(["ditto", "-xk", z, "."])
            except subprocess.CalledProcessError as e:
                print(str(e), file=sys.stderr)
                sys.exit(1)

            # Remove zip file and extra metadata dirs/files
            print(f"Removing {z}")
            try:
                os.remove(z)
            except OSError as e:
                print(str(e), file=sys.stderr)
                sys.exit(1)
            
            try:
                remove_metadata_files()
            except OSError as e:
                print(str(e), file=sys.stderr)
                sys.exit(1)

            # Compress EVT files with gzip
            print("Compressing {}".format(z.split(".")[0]))
            try:
                gzcmd = "pigz {}".format(os.path.splitext(z)[0] + "/*0?-00")
                print(gzcmd)
                subprocess.check_call(gzcmd, shell=True)
            except subprocess.CalledProcessError as e:
                print(str(e), file=sys.stderr)
                sys.exit(1)
        

        try:
            os.chdir("..")
            print(f"Leaving {c}")
        except OSError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
