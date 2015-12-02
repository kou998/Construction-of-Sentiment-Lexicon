#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
基于语料的情感词典构建
@author:kwang
@date:2015-10-27
@version:1.4 
1.将否定词，转折词，虚拟词以及依赖特征的词改由txt文件输入
2.本代码针对COAE的评测语料
3.将原有的三层判别，改成两层判别，即直接根据当前情感以及否定词，放出列表(1.3)
4.原先是针对每句话构建两个列表，现改为针对每个子句构建列表(1.4)
"""
import chardet
import os
import sys
reload(sys)
sys.setdefaultencoding('utf8') 

deny = []
tran = []
unrealist = []
ambiguousword = []

def buildseeddic():
    """
    #把种子词库导入到词典中
    """
    f_seed = open("seedwords.txt", "r")
    posdic = []
    negdic = []
    for line in f_seed.readlines():
        word_score = line.split()
        if word_score[1] == '1':
            if word_score[0] not in posdic:
                posdic.append(word_score[0])
        else:    
            if word_score[0] not in negdic:
                negdic.append(word_score[0])            
            negdic.append(word_score[0])
    return posdic, negdic

def buildstandarddic():
    """
    #把知网词库导入到词典中
    """
    fpos = open("seedpos.txt", "r")
    fneg = open("seedneg.txt", "r")
    posdic = []
    negdic = []
    common = [] #公共词
    for line in fpos.readlines():    #读取知网的pos词
        posdic.append(line.strip())
    #读取知网的neg词，若这个词同时属于pos
    #则不录入negdic，而是录入公共词集common
    for line in fneg.readlines():   
        if line in posdic:
            common.append(line)
            continue
        else:
            negdic.append(line.strip())
    for com in common:    #从posdic中去掉common中的词
        if com in posdic:
            del common[common.index(com)]
    return posdic, negdic

def bulidneeddic():
    """
    构建所需的否定词和转折词列表
    """
    fdeny = open("denydict.txt", "r")  #否定词
    ftran = open("trandict.txt", "r") #转折词
    famb = open('ambigdict.txt','r') #依赖特征的词
    funreal = open('unrealdict.txt','r') #虚拟词
    getdeny = []
    gettran = []
    getamb = []
    getunreal = []
    for word in fdeny.readlines():
        getdeny.append(word.strip())
    for word in ftran.readlines():
        gettran.append(word.strip())
    for word in famb.readlines():
        getamb.append(word.strip())    
    for word in funreal.readlines():
        getunreal.append(word.strip())    
    return getdeny, gettran, getamb, getunreal

def tsplit(string, delimiters):
    """Behaves str.split but supports multiple delimiters."""
    delimiters = tuple(delimiters)
    stack = [string,]
    for delimiter in delimiters:
        for i, substring in enumerate(stack):
            substack = substring.split(delimiter)
            stack.pop(i)
            for j, _substring in enumerate(substack):
                stack.insert(i+j, _substring)
    return stack

def review_reduce():     
    """
    #去掉只有一句话的、用空格断句的句子
    """
    fsourse = open("test.txt", "r")      #原始
    fnew = open("simptxt.txt", "w")    #缩减后
    for review in fsourse.readlines():
        review =  str(review).encode('gbk', 'ignore')
        temp = review.split("，")
        if len(temp)==1 or (len(temp)==2 and temp[1] == ''):
            continue
        else:
            fnew.write(review)    
            
def pos_labeling_changes(str_original, standardpos, standartneg):
    '''
    不同系统分词词性标识统一转变为：< 名词：/n   形容词：/a   副词：/d   (否定词：/f)  动词：/v  连词：/cc >
    str_original：分过词后的字符串
    '''
    #str_original = str_original.replace(',','，/w')
    #str_original = str_original.replace('./m','。/w')
    #str_original = str_original.replace('?','？/w')
    #str_original = str_original.replace('!','！/w')
    #str_original = str_original.replace('：',':/w')
    #str_original = str_original.replace(';','；/w')    
    str_original = str_original.replace('/NN','/n')
    str_original = str_original.replace('/VA','/a')
    str_original = str_original.replace('/AD','/d')
    str_original = str_original.replace('/VV','/v')
    str_original = str_original.replace('/CC','/cc')
    str_original = str_original.replace('/i','/a')
    #标出形容词
    temp = ''
    for word in str_original.split():
        if len(word.split('/')) != 2:
            continue
        if 'a' in word.split('/')[1]:
            tempword = word.split('/')[0] + '/a '
            temp += tempword
        else:
            temp += word + ' '
            
    
    ##强制性纠正形容词的词性
    #for word in str_original.split():
        #if word.split('/')[0] in standardpos or word.split('/')[0] in standartneg:
            #str_original = str_original.replace(word,(word.split('/')[0]+'/a'))          
    return str_original  

def train(posdic, negdic, standardpos, standartneg):       
    """
    根据语法规则构造情感词典
    """
    win = 3  #查找否定词的窗口大小
    samelist = []  #表示与初始情感一致的词
    antilist = []  #表示与初始情感相反的词
    seedposdic = {}  #积极种子词库
    seednegdic = {}  #消极种子词库
    #fsource = open("jiebaoutsb.txt", "r")
    #fsource = open('aa.txt','r')
    path = "../Corpus/Segment_Corpus/all"
    filedir = os.listdir(path)
    fpos = open("pos.txt", "w")
    fneg = open("neg.txt", "w")
    #标记目前所处的状态。
    #1表示逗号连接的都是samelist的词
    #-1表示逗号连接的都是neglist的词
    plor = 1   
    print '-------------------------开始分析-------------------------------'
    for fileid in range(0,len(filedir)):
        getpath = path + os.sep + filedir[fileid]
        review_list = open(getpath, 'r').readlines()
        for review in review_list:
            review = pos_labeling_changes(review, standardpos, standartneg)  #修正分词结果。   
            review = review.strip()
            plor = 1
            #断句，划分多个子句 
            #sent_split = tsplit(review,('。/w', '！/w', '；/w','./w', 
                                      #'？/w', '：/w', '，/w', '、/w'))

            #sent_split = tsplit(review,('。/x', '！/x', '；/x','./x', 
                                      #'？/x', '：/x', '，/x', '、/x'))
            sent_split = tsplit(review,('。/PU', '！/PU', '；/PU','./PU', 
                                        '？/PU'))            
            for subsent in sent_split:  #遍历所有子句
                samelist = []
                antilist = []                
                if subsent == '':     #针对出现多个连续标点
                    continue
                wordlist = subsent.split()
                if len(wordlist) == 0:
                    break
                #如果是虚拟语气，则不处理
                if wordlist[0].split('/')[0] in unrealist:
                    continue                              
                for word in wordlist:
                    if len(word.split('/')) != 2: #防止语料中本身带有‘/’
                        continue                        
                    #取形容词
                    if str(word.split('/')[1]).startswith('a') :
                        #根据窗口值，设置寻找名词的开始位置
                        index = wordlist.index(word)
                        if index-win >= 0:  
                            start = index - win
                        else: #如果窗口范围内是句子的起始，则从起始位置开始
                            start = 0
                        find = False   #如果极性依赖特征，判断是否找到特征。
                        if word.split('/')[0] in ambiguousword:
                            for i in range(index):
                                #一直往前找，找到第一个名词
                                tempsplit = wordlist[index-1-i].split('/')
                                if tempsplit[1] == 'n' : 
                                    #word = 找到的名词+形容词+/a  比如：声音小/a
                                    word = tempsplit[0] + ' ' + word.split('/')[0] + '/a'
                                    find = True
                                    break
                            if find == False:  #未找到不确定词的特征，则舍弃
                                break
                        havedeny = False   #是否有否定词
                        #i = 0
                        for j in range(win):     #根据窗口大小找否定词
                            if start+j >= index:
                                break
                            if wordlist[start+j].split('/')[0] in deny:   
                                havedeny = True
                                #i = j
                                break
                        if wordlist[0].split('/')[0] in tran:
                            plor = 0 - plor
                        #A.如果出现否定词且有转折词  两次否定取正
                        if plor == -1 and havedeny==True:
                            samelist.append(word.split('/')[0])  
                            break
                        elif plor == -1 and havedeny==False:
                            antilist.append(word.split('/')[0])
                            break   
                        elif  plor == 1 and havedeny==True:
                            antilist.append(word.split('/')[0])
                            break                              
                        elif plor == 1 and havedeny==False:
                            samelist.append(word.split('/')[0])  
                            break      
        #规则示例句子：
        #拖把/n 总体/n 还是/d 不错/a ，/w 就是/ 不/c 便宜/a ， 性价比/n 略/d 低/a ，/w
        #但是/c 还是/d 很/d 耐用/a 的/u ，/w 而且/c
        #用/v 起来/v 很/d 舒服/a ，/x 换成/v 别的/n 早就/d 破/a 了/u ，/x 赞/a ！/x
        #运行过程如下：
        #初始plor = 1，列表为空。
        #找到形容词“不错”，没有否定词，句首没有转折词,plor=1,按着规则D，添加到与初始极性相同的列表samelist中；
        #找到形容词“便宜”，窗口范围内有否定词，句首有转折词，plor=1,按照规则A,添加到samelist，变plor=-1
        #找到形容词“低”，窗口范围内没有否定词，句首没有转折词，plor=-1，按照规则B，添加到antilist
        #找到形容词“耐用”，窗口范围内没有否定词，句首有转折词，plor=-1，按照规则C，添加到samelist，变plor=1
        #找到形容词“舒服”，窗口范围内没有否定词，句首没有转折词，plore=1，按照规则D，添加到samelist
        #找到形容词“破”，句首是虚拟语气词，跳过该句。
        #找到形容词“赞”，窗口范围内没有否定词，句首没有转折词，plor=1，按照规则D，添加到samelist。
        #结果：samelist中有“不错”、“便宜”、“耐用”、“舒服”
        #antilist中有“低”
                posinsame = 0   #samelist中的积极词的数量
                neginsame = 0   #samelist中的消极词的数量
                for tempword in samelist:  #遍历已有的正类词，新判断的词添加到posdic中去
                    if tempword in posdic:
                        posinsame += 1           
                for tempword in samelist:    #此处有修改！！！！
                    if tempword in negdic:
                        neginsame += 1
            #说明samelist中正类单词比负类少，samelist为负类
                if (posinsame  < neginsame):   
                    temp = samelist
                    samelist = antilist
                    antilist = temp
            # 这样我们就把samelist变成了正类，antilist变成了负类。  
            #但由于数量少的时候，总有错分的，
            #这时候我们需要再次使用种子词库做比较，根据知网词库，强制纠错。
                for pos in samelist:
                    if pos in standartneg:
                        del  samelist[samelist.index(pos)]
                        antilist.append(pos)
                for neg in antilist:
                    if neg in standardpos:
                        del antilist[antilist.index(neg)]
                        samelist.append(neg)
                
                for word in samelist:       
                    #if word not in posdic:   #更新消极种子词库
                        #posdic.append(word)
                    if seedposdic.has_key(word):   #更新不断扩大的词库
                        seedposdic[word] += 1
                    else:
                        seedposdic.update({word:1})
            
                for  word in antilist:     
                    #if word not in negdic:          #更新消极种子词库
                        #negdic.append(word)
                    if seednegdic.has_key(word):     #更新不断扩大的词库
                        seednegdic[word] += 1
                    else:
                        seednegdic.update({word:1})  
    #对于同属于两类的词，积极的词频大于消极的3倍才算积极的
    alph = 0.25
    for k in seedposdic:         
        if seednegdic.has_key(k):
            if seedposdic[k]*alph > seednegdic[k] * (1 - alph) :
                seednegdic[k] = 0
            else:
                seedposdic[k] = 0
    #合并Hownet中的词
    for i in standardpos:
        if i not in seedposdic:
            seedposdic.update({i:10})
    for i in standartneg:
        if i not in seednegdic:
            seednegdic.update({i:10})
  
    print '----------开始排序-----------------'
    sorted_pos = sorted(seedposdic.iteritems(),  
                        key=lambda d:d[1],  reverse = True )       
    sorted_neg = sorted(seednegdic.iteritems(),  
                        key=lambda d:d[1],  reverse = True )
    print '----------开始写入文件---------------'
    for k in sorted_pos:
        if k[1] > 0 :
            #print 'pos'+str(k[0])
        #if k[1]!=0 :
            #fpos.write(k[0] + ':'+ str(k[1]) +'\n')
            #fpos.write(k[0] +'\t' +'1' +'\t'+ str(k[1]) +'\n')  
            fpos.write(k[0] +'\t' +'1' +'\n') 
            
    for k in sorted_neg:
        if k[1] > 0:
            #print 'neg'+str(k[0])
         #if k[1]!=0 :
              #fneg.write(k[0] + ':'+ str(k[1]) +'\n')    
            #fneg.write(k[0]+'\t' +'-1'  +'\t'+ str(k[1])+'\n')  
            fneg.write(k[0]+'\t' +'-1' + '\n')  
    print '--------结束！---------------'        
if __name__ == '__main__':
    deny,tran, ambiguousword,unrealist = bulidneeddic()
    POSDIC, NEGDIC = buildseeddic()
    HOWNETPOS, HOWNETNEG = buildstandarddic()
    train(POSDIC, NEGDIC, HOWNETPOS, HOWNETNEG)
