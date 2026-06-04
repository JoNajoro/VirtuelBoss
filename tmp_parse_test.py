from parser_service import parse_cotes, parse_resultats
text_result = '''Spurs

2:3

Burnley 35' 39' 71'

51' 62'

MT: 0:2

A. Villa

0:2

Sunderland 61'69'

MT: 0:0

X

West Ham

80'85'

2:0

MT: 0:0

London Blues

Manchester Red

84'

1:2

MT: 0:1

London Reds

28' 60'

Everton

0:1

Wolverhampton

MT: 0:0

59'

Brentford

1' 41' 84' 90'

4:1

MT: 2:0

Leeds

72'

Manchester Blue

65'

1:3

MT: 0:1

Liverpool 20' 85' 86'

Bournemouth

24'

1:2

MT: 1:1

Newcastle 41'74'

Fulham

1:0

47'

MT: 0:0

C. Palace

N. Forest

49'

1:3

MT: 0:1

Brighton 20' 62' 68' '''
text_cote = '''Spurs

Burnley

1,41

5,52

5,84

A. Villa

Sunderland

1,38

5,27

6,93

West Ham

London Blues

2,54

3,69

2,54

Manchester Red

London Reds

4,21

3,55

1,85

Everton

Wolverhampton

1,91

3,42

4,08

Brentford

Leeds

1,37

5,12

7,57

Manchester Blue

Liverpool

1,58

4,81

4,58

Bournemouth

Newcastle

2,88

3,54

2,32

Fulham

C. Palace

2,10

3,63

3,23

N. Forest

Brighton

2,26

3,81

2,82'''
print('RESULTATS ->', parse_resultats(text_result))
print('COTES ->', parse_cotes(text_cote))
