#!/usr/bin/env python
# -*- coding: utf-8 -*-

# http://boto.readthedocs.org/en/latest/ec2_tut.html
import boto
import boto.ec2
import time, sys, getopt, signal, argparse


# This is the script that will be executed on each instance's boot up
startup_script = """#!/bin/bash
apt-get update
apt-get -y install git
apt-get -y install g++
apt-get -y install make
apt-get -y install libqt4-gui
git clone https://github.com/glinscott/fishtest.git
cd fishtest/worker
python worker.py --concurrency {0} {1} {2}
"""

# We select only the "Compute Optimized" types
# http://aws.amazon.com/ec2/instance-types/
INSTANCE_TYPES = [{ 'name': 'c3.xlarge',
					'cores': 4},
				  { 'name': 'c3.2xlarge',
					'cores': 8},
				  { 'name': 'c3.4xlarge',
					'cores': 16},
				  { 'name': 'c3.8xlarge',
					'cores': 32}]

# EC2 reservation Object
reservation = None

def main():

	# https://docs.python.org/2/library/argparse.html#module-argparse
	parser = argparse.ArgumentParser(usage="awsrun.py num_instances instance_type user password\n\nAdd -h for detailed help", 
									 epilog=get_epilog_help_message(), 
									 formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument('num_instances', help='Number of instances to launch', type=int)
	parser.add_argument('instance_type', help='Amazon ec2 instance type', choices=get_instace_types_list())
	parser.add_argument('user', help='User for tests.stockfishchess.org')
	parser.add_argument('password', help='Password for tests.stockfishchess.org')
	parser.add_argument('-dry', dest="dry_run", help='Dry run', action="store_true")
	args = parser.parse_args()

	number_of_cores = get_cores_for(args.instance_type)-1

	print 'Number of instances to launch:', args.num_instances
	print 'Instance Type:', args.instance_type
	print 'Number of cores per instance:', number_of_cores

	print
	print 'Connecting to AWS EC2...'
	
	ec2_conn = boto.ec2.connect_to_region('us-east-1')

	global reservation
	reservation = ec2_conn.run_instances('ami-9eaa1cf6', # Ubuntu 14.04
										 instance_type=args.instance_type, 
										 instance_initiated_shutdown_behavior='terminate', 
										 min_count=args.num_instances, max_count=args.num_instances,
										 user_data=startup_script.format(number_of_cores, args.user, args.password),
										 dry_run=args.dry_run)

	print 'Success. Number of instances launched:', len(reservation.instances)

	# Let's make sure we terminate the instances in case of a CTRL+C
	signal.signal(signal.SIGTERM, handle_sigterm)
	signal.signal(signal.SIGINT, handle_sigterm)

	# wait_for_all_instances_to_run()
	countdown()
	terminate_instances()


def get_epilog_help_message():
	return "The possible values for the instance_type are:\n" + str(get_instace_types_list())


def get_instace_types_list():
	ret = []
	for inst in INSTANCE_TYPES:
		ret.append(inst['name'])
	return ret


def get_cores_for(instance_type):
	for inst in INSTANCE_TYPES:
		if inst['name'] == instance_type:
			return inst['cores']

	raise Exception("Invalid instance_type")


def countdown():
	remaining_time = 3500
	while remaining_time >= 0:
		sys.stdout.write("\rRemaining time before terminating instances: {: <10}\r".format(remaining_time))
		sys.stdout.flush()
		time.sleep(1)
		remaining_time -= 1
	print


def terminate_instances():
	print 'Terminating instances...'
	for instance in reservation.instances:
		instance.terminate()
	print 'All instances terminated...'


def handle_sigterm(signal, frame):
	terminate_instances()
	sys.exit(0)


def wait_for_all_instances_to_run():
	all_running = False

	print 'Waiting for instances to run...'
	while not all_running:
		time.sleep(10)

		all_running = True
		for instance in reservation.instances:
			instance.update()
			print '...instance {} is in {} state'.format(instance.id, instance.state)
			all_running = all_running and instance.state == 'running'
	print 'All instances running...'

if __name__ == "__main__":
	main()