import pandas as pd 
import csv


f = 'Example_Ruby_3_comma_header.asc'

def get_delim(f):
	data = open(f, "r").read()
	delimiter = csv.Sniffer().sniff(data).delimiter
	return delimiter

def get_header(f):
	data = open(f, "r").read()
	hasheader = csv.Sniffer().has_header(data)
	return hasheader

delim1 = get_delim(f)


a = pd.read_csv(f, sep=delim1, skip_blank_lines=True)

print(a)
print(delim1)
print(  get_header(f) )