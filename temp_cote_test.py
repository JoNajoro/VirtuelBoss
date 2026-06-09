from parser_service import parse_cotes
samples = [
    'Spurs\n\nBurnley\n1,41 5,52 5,84\n',
    'Spurs vs Burnley\n1,41 5,52 5,84\n',
    'Spurs - Burnley\n1,41\n5,52 5,84\n',
    'Spurs\nBurnley\n1,41\n5,52\n5,84\n',
    'Spurs 1,41 5,52 5,84\n',
]
for s in samples:
    print('---')
    print(repr(s))
    print(parse_cotes(s))
