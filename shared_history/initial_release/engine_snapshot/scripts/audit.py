#!/usr/bin/env python3
"""Mechanical PDF/source audit, separate from scientific and authorship gates."""
from pathlib import Path
import sys,re,json,hashlib,subprocess
import fitz
ROOT=Path(__file__).resolve().parents[1]

def audit_pdf(path):
    path=Path(path);d=fitz.open(path)
    pages=[];out=[];standards=[];text=''
    for i,p in enumerate(d):
        t=p.get_text();text+=t+'\n';pages.append({'page':i+1,'width_pt':p.rect.width,'height_pt':p.rect.height,'text_characters':len(t)})
        for block in p.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for span in line.get('spans',[]):
                    if not span['text'].strip():continue
                    x0,y0,x1,y1=span['bbox']
                    if x0<52 or x1>561 or y0<70 or y1>724:
                        out.append({'page':i+1,'text':span['text'],'bbox':list(span['bbox'])})
                    if 'Nimbus' in span['font'] or 'DejaVu' in span['font']:
                        standards.append(span['size'])
    fonts=subprocess.check_output(['pdffonts',str(path)],text=True)
    flags=[re.search(r'\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$',line) for line in fonts.splitlines()[2:]]
    embedded=bool(flags) and all(m and m.group(1)=='yes' for m in flags)
    last_refs=(len(d)<5 or bool(re.match(r'^\s*\d+\.\s*REFERENCES',d[4].get_text())))
    footer_text=any(any(w[1]>742 for w in p.get_text('words')) for p in d)
    return {'path':str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),'pages':len(d),'geometry':pages,
            'bytes':path.stat().st_size,'size_under_5MB':path.stat().st_size<5_000_000,
            'letter_size':all(abs(p.rect.width-612)<.1 and abs(p.rect.height-792)<.1 for p in d),
            'all_fonts_embedded':embedded,'no_type3':'Type 3' not in fonts,'font_report':fonts,
            'ordinary_text_min_pdf_pt':min(standards),'ordinary_text_at_least_9_TeX_pt':min(standards)>=8.94,
            'font_note':'9 TeX pt = 8.966 PDF pt. Math scripts and operator extensions are excluded from ordinary text audit.',
            'text_outside_toleranced_print_area':out,'fifth_page_starts_references':last_refs,
            'no_footer_text':not footer_text,'unresolved_references':'??' in text,
            'ai_disclosure':'ChatGPT (OpenAI)' in text and 'AI DISCLOSURE' in text,
            'authorship_complete':'Author information required before submission' not in text,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def main():
    protocol=json.loads((ROOT/'configs/frozen_protocol.json').read_text())
    hash_checks={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in protocol['source_sha256'].items()}
    reports={name:audit_pdf(ROOT/'papers'/name/'main.pdf') for name in ['recheck','repairlens']}
    for name,r in reports.items():
        log=(ROOT/'papers'/name/'main.log').read_text(errors='replace')
        r['latex_overfull_count']=log.count('Overfull')
        r['latex_undefined_reference_warning']='undefined references' in log or 'undefined on input line' in log
        s=(ROOT/'papers'/name/'main.tex').read_text();a=s.split('\\begin{abstract}')[1].split('\\end{abstract}')[0]
        r['abstract_word_count_approx']=len(re.sub(r'\\[A-Za-z]+','VALUE',a).split())
        r['mechanical_format_checks_pass']=all([r['pages']<=5,r['size_under_5MB'],r['letter_size'],r['all_fonts_embedded'],r['no_type3'],r['ordinary_text_at_least_9_TeX_pt'],not r['text_outside_toleranced_print_area'],r['fifth_page_starts_references'],r['no_footer_text'],not r['unresolved_references'],r['ai_disclosure'],r['latex_overfull_count']==0,not r['latex_undefined_reference_warning']])
    result={'frozen_policy_source_hashes_unchanged':hash_checks,'papers':reports,
            'submission_ready':False,'blockers':['Real author names, affiliations and ORCiD not supplied','No real LLM/public benchmark/natural-failure experiments','Known-model theoretical results do not establish broad novelty','No independent human scientific/code review','RepairLens assigned-operation savings do not translate into measured local speedup'],
            'template':'Official 2027 spconf executable definitions transcribed through web text; not a byte-identical downloaded archive. See upstream/provenance.json.',
            'visual_review':'Every manuscript page rendered and inspected; visual review is by the same assistant, not an independent reviewer.'}
    (ROOT/'results/final_audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:{'pages':v['pages'],'mechanical_format_checks_pass':v['mechanical_format_checks_pass'],'ordinary_text_min_pdf_pt':v['ordinary_text_min_pdf_pt'],'out_of_bounds':v['text_outside_toleranced_print_area']} for k,v in reports.items()},indent=2))
    if not all(hash_checks.values()) or not all(r['mechanical_format_checks_pass'] for r in reports.values()):sys.exit(1)

if __name__=='__main__':main()
