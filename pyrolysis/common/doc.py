def parse_docstring(v):
    doc_params = {}
    doc_excep = {}
    doc_return = ''
    summary = ''
    desc = ''
    mode = 0
    if v:
        for l in v.split('\n'):
            if len(l) == 0:
                if mode == 1:
                    mode = 2
            elif ':param' in l:
                p = l.find(':param')
                p2 = l.find(':', p + 1)
                name = l[p + 6:p2].strip()
                val = l[p2 + 1:].strip()
                doc_params[name] = val
                mode = -1
            elif ':raise' in l:
                p = l.find(':raise')
                p2 = l.find(':', p + 1)
                name = l[p+6:p2].strip()
                val = l[p2+1:].strip()
                doc_excep[name] = val
                mode = -1
            elif ':return' in l:
                p = l.find(':return')
                p2 = l.find(':', p + 1)
                doc_return = l[p2+1:].strip()
                mode = -1
            else:
                if mode == 0 or mode == 1:
                    mode = 1
                    if summary != '':
                        summary += '\n'
                    summary += l.strip()
                if mode == 2:
                    if desc != '':
                        desc += '\n'
                    desc += l.strip()
    return summary.strip(), desc, doc_params, doc_return, doc_excep
