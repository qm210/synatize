import math
import numpy as np
import pyperclip
import re
import sys

GLfloat = lambda f: str(int(f)) + '.' if f==int(f) else str(f)[0 if f >= 1 else 1:]

syn_file = sys.argv[1] if len(sys.argv) > 1 else 'syn_template'

def GLstr(s):
    try:
        f = float(s)
    except ValueError:
        return s
    else:
        return GLfloat(f)

syncode = ""

#reserved keywords you cannot name a form after ~ f,t are essential, and maybe we want to use the other
_f = {'ID':'f', 'type':'uniform'}
_t = {'ID':'t', 'type':'uniform'}
_B = {'ID':'B', 'type':'uniform'}
_vel = {'ID':'vel', 'type':'uniform'}
_Bsyn = {'ID':'Bsyn', 'type':'uniform'}
_Bproc = {'ID':'Bproc', 'type':'uniform'}
_Bprog = {'ID':'Bprog', 'type':'uniform'}
_L = {'ID':'L', 'type':'uniform'}
_tL = {'ID':'tL', 'type':'uniform'}
_SPB = {'ID':'SPB', 'type':'uniform'}
_BPS = {'ID':'BPS', 'type':'uniform'}
_BPM = {'ID':'BPM', 'type':'uniform'}
_note = {'ID':'note', 'type':'uniform'}
form_list = [_f, _t, _B, _vel, _Bsyn, _Bproc, _Bprog, _L, _tL, _SPB, _BPS, _BPM, _note]

main_list = []

newlineplus = '\n'+6*' '+'+'

def main():

    global synhead
    global syncode
    global form_list
    global main_list
   
    print('READING', './' + syn_file + ':')
   
    with open(syn_file,"r") as template:
        lines = template.readlines()
        
    for l in lines:
        if l=='\n' or l[0]=='#': continue
    
        line = l.split()
        cmd = line[0]
        cid = line[1]
        arg = line[2:]
       
        print(line)
        if cmd != 'main' and cid in [f['ID'] for f in form_list]:
            print(' -> ERROR! ID \"' + cid + '\" already taken. Ignoring line.')
            continue

        if cmd == 'main':
            main_list.append({'ID':'main', 'type':'main', 'amount':len(line)-1, 'terms':line[1:]})

        elif cmd == 'const':
            form_list.append({'ID':cid, 'type':cmd, 'value':float(arg[0])})
    
        elif cmd == 'osc' or cmd == 'lfo':
            form_list.append({'ID':cid, 'type':cmd, 'shape':arg[0], 'freq':arg[1], 'phase':arg[2] if len(arg)>2 else '0', 'par':arg[3] if len(arg)>3 else '0'})

        elif cmd == 'env': #env NAME adsr a d s r
            shape = arg[0]
            form = {'ID':cid, 'type':cmd, 'shape':shape}
            
            if shape == 'adsr' or shape == 'adsrexp':
                form.update({'attack':arg[1], 'decay':arg[2], 'sustain':arg[3], 'release':arg[4], 'par':arg[5] if len(arg)>5 else ''})
            elif shape == 'doubleslope':
                form.update({'attack':arg[1], 'decay':arg[2], 'sustain':arg[3], 'par':arg[4] if len(arg)>4 else ''})
            elif shape == 'ss':
                form.update({'attack':arg[1], 'par':arg[2] if len(arg)>2 else ''})
            elif shape == 'ssdrop':
                form.update({'decay':arg[1], 'par':arg[2] if len(arg)>2 else ''})
            elif shape == 'expdecay':
                form.update({'decay':arg[1], 'par':arg[2] if len(arg)>2 else ''})
            else:
                pass
            
            form_list.append(form)

        # global automation curve - no idea on how to parametrize, but have that idea in mind
        elif cmd == 'gac':
            pass

        # advanced forms ("operators"), like detune, chorus, delay, waveshaper/distortion, and more advanced: filter, reverb
        elif cmd == 'form':
            op = arg[0]
            form = {'ID':cid, 'type':cmd, 'OP':op}

            if op == 'mix':
                form.update({'amount':len(arg), 'terms':arg[1:]})
            elif op == 'detune':
                form.update({'source':arg[1], 'amount':arg[2]})
            elif op == 'pitchshift':
                form.update({'source':arg[1], 'steps':arg[2]})
            elif op == 'quantize':
                form.update({'source':arg[1], 'quant':arg[2]})
            elif op == 'overdrive':
                form.update({'source':arg[1], 'gain':arg[2]})
            elif op == 'chorus':
                form.update({'source':arg[1], 'number':arg[2], 'delay':arg[3]})
            elif op == 'delay':
                form.update({'source':arg[1], 'number':arg[2], 'delay':arg[3], 'decay':arg[4]})
            elif op == 'waveshape':
                form.update({'source':arg[1], 'par':arg[2:8]})
            elif op == 'saturate':
                form.update({'source':arg[1], 'gain':arg[2], 'mode':arg[3] if len(arg)>3 else 'default'})
            else:
                pass
                
            form_list.append(form)

        
    if not main_list:
        print("WARNING: no main form defined! will return empty sound")
        syncode = "s = 0.; //some annoying weirdo forgot to define the main form!"

    else:
        if len(main_list)==1:
            syncode = "s = "
            for term in main_list[0]['terms']:
                syncode += instance(term) + (newlineplus if term != main_list[0]['terms'][-1] else ';')
           
        else:
            syncount = 1
            for form_main in main_list:
                syncode += 'if(Bsyn == ' + str(syncount) + '){\n' + 6*' ' + 's = '
                for term in form_main['terms']:
                    syncode += instance(term) + (newlineplus if term != form_main['terms'][-1] else ';')
                syncode += '}\n' + 4*' '
                syncount += 1

        syncode = syncode.replace('_TIME','t').replace('_RESETTIME','_t').replace('vel*','').replace('e+00','')

    gf = open("syn_framework")
    glslcode = gf.read()
    gf.close()

    print("\nBUILD SYN CODE:\n", 4*' '+syncode, sep="")
    
    BPM = 80
    note = 24

    glslcode = glslcode.replace("//SYNCODE",syncode) \
                       .replace("const float note = 24.;", "const float note = " + GLfloat(note) + ";") \
                       .replace("const float BPM = 80.;", "const float BPM = " + GLfloat(BPM) + ";")

    pyperclip.copy(glslcode)
    print("\nfull shader written to clipboard")

def instance(ID, mod={}):
    
    form = next((f for f in form_list if f['ID']==ID), None)
    
    if mod:
        form = form.copy()
        form.update(mod)
    
    if '*' in ID:
        IDproduct = ID.split('*')
        product = ''
        for factorID in IDproduct:
            product += instance(factorID) + ('*' if factorID != IDproduct[-1] else '')
        return product;

    elif not form:
        return GLstr(ID)
    
    elif form['type']=='uniform':
        return ID
    
    elif form['type']=='const':
        return GLfloat(form['value'])
    
    elif form['type']=='form':
        if form['OP'] == 'mix':
            return '(' + '+'.join([instance(f) for f in form['terms']]) + ')' 
        elif form['OP'] == 'detune':
            return 's_atan(' + instance(form['source']) + '+' + instance(form['source'],{'freq':'(1.-' + instance(form['amount']) + ')*'+param(form['source'],'freq')}) + ')'
        elif form['OP'] == 'pitchshift':
            return instance(form['source'],{'freq':'{:.4f}'.format(pow(2,float(form['steps'])/12)) + '*' + param(form['source'],'freq')})
        elif form['OP'] == 'quantize':
            return instance(form['source']).replace('_TIME','floor('+instance(form['quant']) + '*_TIME+.5)/' + instance(form['quant']))
        elif form['OP'] == 'overdrive':
            return 'clip(' + instance(form['gain']) + '*' + instance(form['source']) + ')'
        elif form['OP'] == 'chorus': #not finished, needs study
            return '(' + newlineplus.join([instance(form['source']).replace('_TIME','(_TIME-'+'{:.1e}'.format(t*float(form['delay']))+')') for t in range(int(form['number']))]) + ')'
        elif form['OP'] == 'delay': #not finished, needs study
            return '(' + newlineplus.join(['{:.1e}'.format(pow(float(form['decay']),t)) + '*' + \
                                           instance(form['source']).replace('_RESETTIME','(_RESETTIME-'+'{:.1e}'.format(t*float(form['delay']))+')') for t in range(int(form['number']))]) + ')'
        elif form['OP'] == 'waveshape':
            return 'supershape(' + instance(form['source']) + ',' + ','.join(instance(form['par'][p]) for p in range(6)) + ')'
        elif form['OP'] == 'saturate':
            if form['mode'] == 'crazy':
                return 's_crzy('+instance(form['gain']) + '*' + instance(form['source']) + ')'
            else:
                return 's_atan('+instance(form['gain']) + '*' + instance(form['source']) + ')'
        else:
            return '1.'

    elif form['type']=='osc' or form['type']=='lfo':

            if form['type'] == 'osc':
                phi = instance(form['freq']) + '*_TIME'
                pre = 'vel*'

            elif form['type'] == 'lfo':
                phi = instance(form['freq']) + ('*Bprog' if form['par'] != 'time' else '*_TIME')
                pre = ''
                if form['shape'] == 'squ': form['shape'] = 'psq'

                
            if form['shape'] == 'sin':
                if form['phase'] == '0':
                    return pre + '_sin(' + phi + ')'
                else:
                    return pre + '_sin(' + phi + ',' + instance(form['phase']) + ')'
  
            elif form['shape'] == 'saw':
                return pre + '(2.*fract(' + phi + '+' + instance(form['phase']) + ')-1.)'
            
            elif form['shape'] == 'squ':
                if form['par'] == '0':
                    return pre + '_sq(' + phi + ')'
                else:
                    return pre + '_sq(' + phi + ',' + instance(form['par']) + ')'

            elif form['shape'] == 'psq':
                if form['par'] == '0':
                    return pre + '_psq(' + phi + ')'
                else:
                    return pre + '_psq(' + phi + ',' + instance(form['par']) + ')'

            elif form['shape'] == 'tri':
                    return pre + '_tri(' + phi + '+' + instance(form['phase']) + ')'

            else:
                return '0.'

    elif form['type']=='env':
        if form['shape'] == 'adsr':
            return 'env_ADSR(_RESETTIME,tL,'+instance(form['attack'])+','+instance(form['decay'])+','+instance(form['sustain'])+','+instance(form['release'])+')'
        elif form['shape'] == 'adsrexp':
            return 'env_ADSRexp(_RESETTIME,tL,'+instance(form['attack'])+','+instance(form['decay'])+','+instance(form['sustain'])+','+instance(form['release'])+')'
        elif form['shape'] == 'doubleslope':
            return 'doubleslope(_RESETTIME, '+instance(form['attack'])+','+instance(form['decay'])+','+instance(form['sustain'])+')'
        elif form['shape'] == 'ss':
            return 'smoothstep(0.,'+instance(form['attack'])+',_RESETTIME)'
        elif form['shape'] == 'ssdrop':
            return 'theta('+'_RESETTIME'+')*smoothstep('+instance(form['decay'])+',0.,_RESETTIME)'
        elif form['shape'] == 'expdecay':
            return 'theta('+'_RESETTIME'+')*exp(-'+instance(form['decay'])+'*_RESETTIME)'
        else:
            return '1.'

    else:
        return '1.'

def param(ID, key):
    form = next((f for f in form_list if f['ID']==ID), None)
    try:
        value = form[key]
    except KeyError:
        return ''
    except TypeError:
        return ''
    else:
        return value

if __name__ == '__main__':
    main()
