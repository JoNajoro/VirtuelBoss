from parser_service import parse_cotes, _detecter_format_cotes, _parse_cotes_separe, _parse_cotes_inline_simple, nettoyer_lignes
text = 'Spurs\n\nBurnley\n1,41 5,52 5,84\n'
lines = nettoyer_lignes(text)
print('lines', lines)
print('fmt', _detecter_format_cotes(lines))
print('parse_cotes', parse_cotes(text))
print('inline_simple', _parse_cotes_inline_simple(lines))
print('separe', _parse_cotes_separe(lines))
