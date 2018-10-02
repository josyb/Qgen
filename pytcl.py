'''
Created on 28 Jun 2015

@author: Josy
'''
from __future__ import print_function
import sys
import argparse


if __name__ == '__main__':
        parser = argparse.ArgumentParser(description = 'pytcl')
        parser.add_argument('-v', '--verbose', action ='store_true', help='Verbose - print out what happens along the way')
        parser.add_argument('-e', '--QsysElaborate', nargs = '*')
        args = parser.parse_args()

        def tt( l ):
            return 'lwidth_d', 100, 'lwidth_q',  l[1] ,  'someVal', 1234 , 'someBool', True
        
        if args.verbose:
#             print( 'pytcl stdout: <{}>'.format( args.QsysElaborate ), file = sys.stdout)
#             print( 'pytcl stdout: <', file = sys.stdout)
#             for item in args.QsysElaborate:
            print( tt( args.QsysElaborate ), file = sys.stdout )
#             print('>')
#         print( "pytcl stderr : {}".format(args.QsysElaborate), file = sys.stderr)
#         while True:
#             pass
#         raise ValueError( "Just forcing exit")
        sys.exit( 0 )