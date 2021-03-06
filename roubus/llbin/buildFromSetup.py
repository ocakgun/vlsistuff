#! /usr/bin/python

import os,sys,string,types
import instancesLib

def main():
    Fsetupname = sys.argv[1]
    File = open(Fsetupname)
    Lines = File.readlines()
    File.close()
    workLines(Lines)
    db.wires()
#    db.dump()
    db.verilog()
    db.graph()

def workLines(Lines):
    Big = ''
    for line in Lines:
        if '#' in line:
            line = line[:line.index('#')]
        Big += line[:-1]+' '
    Big = string.replace(Big,'->',' -> ')
    Lines = string.split(Big,';')
    for lnum,line in enumerate(Lines):
        wrds = string.split(line)
        if (len(line)<2)or(len(wrds)<1):
            pass
        elif wrds[0][0] in ['#','/']:
            pass
        elif wrds[0]=='instance':
            addInstance(wrds[1:],lnum)
        elif '->' in line:
            addConns(wrds,lnum)
        elif wrds[0]=='default':
            setDefault(wrds[1:],lnum)
        else:
            log_error('unrecognized lnum=%d: "%s"'%(lnum,line))
            return


class dbClass:
    def __init__(self):
        self.instances={}
        self.conns={}
        self.defaults={}
        self.netnames={}
    def evalx(self,What):
        try:
            return eval(What)
        except:
            return What

    def dump(self):
        for Inst in self.instances:
            self.instances[Inst].dump()

    def graph(self):
        Module = self.getDef('module','noc')
        Fout = open('%s.dot'%Module,'w')
        Fout.write('digraph %s {\n'%Module)

        Ins = {}
        Ous = {}
        for Inst in self.instances:
            Obj = self.instances[Inst]
            for Pin in Obj.conns:
                Net = Obj.conns[Pin]
                if 'IN' in Pin:
                    Ins[Net]=Inst
                elif 'OUT' in Pin:
                    Ous[Net]=Inst
                else:
                   print '>>>>',Pin


        for Inst in self.instances:
            Obj = self.instances[Inst]
            Type = Obj.Type
            if 'type' in Obj.Props:
                Typev = Obj.Props['type']
            else:
                Typev = Type
            Dwid = db.getProp('DWID',Obj.Props)
            Depth = db.getProp('depth',Obj.Props,0)
            if Type=='admin':
                Fout.write('%s [color="red";label="%s/%s"];\n'%(Inst,Inst,Dwid))
            elif Depth>0:
                Fout.write('%s [color="green";label="%s/%s*%s"];\n'%(Inst,Inst,Depth,Dwid))
            else:
                Fout.write('%s [label="%s/%s"];\n'%(Inst,Inst,Dwid))
        for Net in Ins:
            To = Ins[Net]
            if Net in Ous:
                From = Ous[Net]
            else:
                From = Net
            Fout.write('%s -> %s;\n'%(From,To))

        Fout.write('}\n')
        Fout.close()
        os.system('dot %s.dot -Tpng -o%s.png'%(Module,Module))




    def verilog(self):
        Module = self.getDef('module','noc')
        Fout = open('%s.v'%Module,'w')
        Clk = self.getDef('clk')
        Rstn = self.getDef('rst_n')
        Big0 = 'module %s (input %s, input %s\n'%(Module,Clk,Rstn)
        Big2 = ''
        for Inst in self.instances:
            Obj = self.instances[Inst]
            Type = Obj.Type
            if 'type' in Obj.Props:
                Typev = Obj.Props['type']
            else:
                Typev = Type
            Dwid = db.getProp('DWID',Obj.Props)
            Depth = db.getProp('depth',Obj.Props,0)
            Id = db.getProp('id',Obj.Props,0)
            Pages = db.getProp('pages',Obj.Props,1)
            Base = instancesLib.getInst(Type)
            Clk = db.getProp('clk',Obj.Props,'clk')
            Trans = [(3,'CLK',Clk),(4,'INST',Inst),(6,'DWIDPY',Dwid),(3,'ANT',Typev),(7,'DEPTHPY',Depth),(7,'SELF_ID',Id),(5,'PAGES',Pages)]
            for Pin in Obj.conns:
                Sig = Obj.conns[Pin]
                Trans.append((len(Pin),Pin,Sig))
            Trans.sort()
            Trans.reverse()
            for (_,Pin,Con) in Trans:
                Base = string.replace(Base,Pin,str(Con))

            Big2 += Base+'\n'
        
        Bigio,Bigw = self.extractWires(Big2)
        Fout.write(Big0)
        Fout.write(Bigio)
        Fout.write(');\n')
        Fout.write(Bigw)
        Fout.write(Big2)
        Fout.write('endmodule\n')
        Fout.close()

    def getProp(self,Prop,Pool,Def=''):
        if Prop in Pool: return Pool[Prop]
        return self.getDef(Prop,Def)

    def getDef(self,Param,Def=''):
        if Param in self.defaults: return self.defaults[Param]
        if Def=='':
            log_error('getDef has no value for %s'%Param)
            return Param
        return Def
        

    def wires(self):
#        for Dir,Who in self.conns:
#            print 'wires %s %s <> %s '%(Dir,Who,self.conns[(Dir,Who)])

        Net = 0
        for (Dir,Who) in self.conns:
            if (Dir,Who) in self.netnames:
                Sig = self.netnames[(Dir,Who)]
            else:
                Sig = 'net%s'%Net
                Net += 1
            Other = self.conns[(Dir,Who)]
            Odir = otherDir(Dir)
            if type(Who)==types.StringType:
                Pin = Dir
                Inst = Who
            else:
                Pin = '%s%s'%(Dir,Who[1])
                Inst = Who[0]
            self.instances[Inst].addConn(Pin,Sig)

            if type(Other)==types.StringType:
                Pin = Odir
                Inst = Other
            else:
                Pin = '%s%s'%(Odir,Other[1])
                Inst = Other[0]

            self.instances[Inst].addConn(Pin,Sig)
                

    def extractWires(self,Big2):
        Bigw = ''
        Bigio = ''

        Wires={}
        Lines = string.split(Big2,'\n')
        Type = 'strange'
        Inst = 'strange'
        for line in Lines:
            for Chr in '.(),':
                line = string.replace(line,Chr,' %s '%Chr)
            wrds = string.split(line)
            if len(wrds)<2:
                pass
            elif wrds[1] in self.instances:
                Inst = wrds[1]
                Type = wrds[0]
            elif wrds[1] == '#':
                wrds1 = wrds[2:]
                Inst = extractInst(wrds[2:])
                if  Inst in self.instances:
                    Type = wrds[0]
                else:
                    log_error('inst %s not in instances "%s"'%(Inst,line))
            else:
                while '.' in wrds:
                    ind = wrds.index('.')
                    Pin = wrds[ind+1]
                    if (wrds[ind+2]=='(')and(wrds[ind+4]==')'):
                        Dir,WW = instancesLib.getPinWid(Type,Pin)
                        if WW=='WID':
                            try:
                                WW = int(self.instances[Inst].Props['wid'])
                            except:
                                WW = int(self.getDef('DWID'))
                            WW += 32+9+2
                                
                        Sig = wrds[ind+3]
                        if Sig[0] in '0123456789-':
                            pass
                        elif Sig not in Wires:
                            Wires[Sig]=WW
                            if Dir=='wire':
                                if int(WW)==1:
                                    Bigw += 'wire %s;\n'%(Sig)
                                else:
                                    Bigw += 'wire [%s-1:0] %s;\n'%(WW,Sig)
                            else:
                                if int(WW)==1:
                                    Bigio += '   ,%s %s\n'%(Dir,Sig)
                                else:
                                    Bigio += '   ,%s [%s-1:0] %s\n'%(Dir,WW,Sig)
                        elif (Wires[Sig]!=WW):
                            log_error('wire %s changed wid from %s to %s'%(Sig,Wires[Sig],WW))

                    wrds = wrds[ind+1:]
        return Bigio,Bigw





def extractInst(wrds):
    while True:
        if wrds==[]: return 'bad'
        if len(wrds)>=3:
            if (wrds[0]==')')and(wrds[2]=='('):
                return wrds[1]
        wrds.pop(0)

    

def otherDir(Dir):
    if Dir[0]=='i': return 'OUT'
    return 'IN'

class instanceClass:
    def __init__(self,Inst,Type):
        self.Inst=Inst
        self.Type=Type
        self.Props={}
        self.conns={}
    def addConn(self,Pin,Net):
        if Pin in self.conns:
            log_error('addConn %s %s double pin=%s net=%s was=%s'%(self.Inst,self.Type,Pin,Net,self.conns[Pin]))
        self.conns[Pin]=Net

    def dump(self):
        print '>> %s type=%s %s conns:'%(self.Inst,self.Type,self.Props)
        for Pin in self.conns:
            print '       %s=%s'%(Pin,self.conns[Pin])
        print

db = dbClass()

def addInstance(wrds,lnum):
    Inst = wrds[0]
    Type = wrds[1]
    obj = instanceClass(Inst,Type)
    db.instances[Inst]=obj
    for wrd in wrds[2:]:
        if '=' in wrd:
            ww = string.split(wrd,'=')
            Var = ww[0]
            Val = db.evalx(ww[1])
            obj.Props[Var]=Val
        else:
            log_error('addInstance got "%s"'%str(wrds))
        
def addClockChange(Clka,Clkb):
    Inst = '%s_%s_chng'%(Clka,Clkb)
    obj = instanceClass(Inst,'changeclk')
    db.instances[Inst]=obj
    obj.Props['clka']=Clka
    obj.Props['clkb']=Clkb
    return Inst



def addConns(wrds,lnum):
    if (len(wrds)==4)and(wrds[1]=='->')and('=' in wrds[3]):
        ww = string.split(wrds[3],'=')
        if ww[0]=='name':
            Name = ww[1]
        else:
            log_error('addConn explicit name got "%s"'%(str(wrds)))
            Name=''
        addConn(wrds[0],wrds[2],Name)
        return

    while len(wrds)>=3:
        if wrds[1]=='->':
            addConn(wrds[0],wrds[2])
            wrds = wrds[2:]
        else:
            log_error('addConns wrds=%s'%str(wrds))
            return
    if len(wrds)!=1:
        log_error('addConns wrds=%s'%str(wrds))


def addConn(From,To,Name=''):
    Fromx = checkConn(From)
    Tox = checkConn(To)
    Clka = db.getProp('clk',db.instances[Fromx].Props,'clk')
    Clkb = db.getProp('clk',db.instances[Tox].Props,'clk')

    if Clka!=Clkb:
        CC = addClockChange(Clka,Clkb)
        print '>>>>>',From,To,Fromx,Tox,Clka,Clkb
    else:
        db.conns[('OUT',Fromx)] = Tox
    if Name!='':
        db.netnames[('OUT',Fromx)]=Name
#    db.conns[('IN',Tox)] = Fromx

def checkConn(Text):
    if ':' in Text:
        ww = string.split(Text,':')
        return (ww[0],ww[1])
    return Text

def setDefault(wrds,lnum):
    if len(wrds)==2:
        db.defaults[wrds[0]] = db.evalx(wrds[1])
    else:
        log_error('setDefault wrds=%s'%str(wrds))

def log_error(Txt):
    print 'Error! %s'%Txt


instancesLib.log_error = log_error








main()

    

