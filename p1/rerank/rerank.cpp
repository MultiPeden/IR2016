
#include <math.h>
#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <map>
#include <list>
#include <iterator>
#include <vector>
#include <typeinfo>
#include <algorithm>
#include "indri/Combiner.hpp"
#include "indri/Repository.hpp"
#include "indri/CompressedCollection.hpp"
#include "indri/LocalQueryServer.hpp"
#include "indri/ScopedLock.hpp"
#include "indri/DocListFileIterator.hpp"
using namespace std;



struct QueryDoc {
    string docName;
    string docId;
    int score;
    float R1_score;
    float R2_score;
    int rank;
    int R1_rank;
    int R2_rank;
    int R1R2_rank;
};


// stuct for info about terms
struct TermInfo {
    int count;
    int docCount;
    double tf_idf;
};

// Converts integers to string
#define int2str(x) static_cast< std::ostringstream & >( \
(std::ostringstream() << std::dec << x)).str()



// Extract the index's doc id from the docid from
// the docno(from the IndriRunQuery result file)
string get_document_id(indri::collection::Repository& r, const char* av) {
    indri::collection::CompressedCollection* collection = r.collection();
    std::string attributeValue = av;
    std::vector<lemur::api::DOCID_T> documentIDs;
    documentIDs = collection->retrieveIDByMetadatum("docno", attributeValue);

    return int2str(documentIDs[0]);
}


int termInDocs(indri::collection::Repository& r, const std::string& termString) {
    std::string stem = r.processTerm(termString);
    indri::server::LocalQueryServer local(r);
    int counter = 0;
    indri::collection::Repository::index_state state = r.indexes();

    for ( size_t i = 0; i < state->size(); i++ ) {
        indri::index::Index* index = (*state)[i];
        indri::thread::ScopedLock(index->iteratorLock());

        indri::index::DocListIterator* iter = index->docListIterator(stem);
        if (iter == NULL) continue;

        iter->startIteration();
        for (iter->startIteration(); iter->finished() == false; iter->nextEntry()) {
            counter = counter + 1;
        }
        delete iter;
    }
    return counter;
}


// Split a string, by a delimitor char, into a vector
vector<string> split(const string &str, char delim) {
    stringstream ss(str);
    string item;
    vector<string> tokens;
    while (getline(ss, item, delim)) {
        tokens.push_back(item);
    }
    return tokens;
}


// get doc info and remove stopwords
pair< int , map<string, TermInfo> > getDocInfo(indri::collection::Repository& r, const char* number) {
    map<string, TermInfo > terms;
    int termsInDoc = 0;
    indri::server::LocalQueryServer local(r);
    lemur::api::DOCID_T documentID = atoi(number);
    std::vector<lemur::api::DOCID_T> documentIDs;
    documentIDs.push_back(documentID);
    indri::server::QueryServerVectorsResponse* response = local.documentVectors(documentIDs);

    if ( response->getResults().size() ) {
        indri::api::DocumentVector* docVector = response->getResults()[0];
        for ( size_t i = 0; i < docVector->positions().size(); i++ ) {
            int position = docVector->positions()[i];
            const std::string& stem = docVector->stems()[position];
            if (position) {  // not a stopword
                termsInDoc = termsInDoc += 1;
                map<string, TermInfo>::iterator  t = terms.find(stem);
                if ((t == terms.end())) {
                    TermInfo termInfo;
                    termInfo.count = 1;
                    terms.insert(std::map<string, TermInfo>::value_type(stem, termInfo));
                } else {
                    t->second.count += 1;
                }
            }
        }
        delete docVector;
    }
    delete response;
    return make_pair< int , map<string, TermInfo> >(termsInDoc, terms);
}


// load documents info from the result of IndriRunQuery from a file,
// get the documents internal index docid, and save date into a vector
// of QueryDoc structs
map<int,  vector<QueryDoc>  >  loadRes (indri::collection::Repository& r, char* resfile) {
    map<int,  vector<QueryDoc>  > queries;
    string line;
    ifstream file(resfile);
    string          padding;
    string          docName;
    int             Qid;
    int             rank;
    int             score;
    int             padding1;

    if (file.is_open()) {
        while (getline(file, line)) {
            // Read the docinfo from the result file udsing a string stream
            stringstream linestream(line);
            linestream >> Qid >> padding >> docName >> rank >> score >> padding1;
            // Store the info in a QueryDoc struct
            QueryDoc query;
            query.docName = docName;
            query.rank  = rank;
            query.score = score;
            // convert string to const char *
            const char * c = docName.c_str();
            query.docId = get_document_id(r, c);
            // push query with Qid to the map
            queries[Qid].push_back(query);
        }
    } else {cout << "Unable to open file";
        }
    return queries;
}


map < string , vector<string> >  loadQueries() {
    map < string , vector<string> >  queriesMap;
    string line;
    ifstream rankfile("./queriesReRank.txt");
    if (rankfile.is_open()) {
        while (getline(rankfile, line)) {
            vector<string> query = split(line, ',');
            string Qid = split(query[0], ' ')[0];
            vector<string> Qterms = split(query[1], ' ');
            queriesMap.insert( map < string , vector<string> >::value_type(Qid, Qterms));
        }
        rankfile.close();
        return queriesMap;
    }
    else {
        cout << "Unable to open file";
      }
    return queriesMap;
}

double TFIDF(int tInDoc, int docLen, int totalDocs,  int tInDocs) {
    double TF;
    double IDF;
    // TF(t) = (Number of times term t appears in the document) / (Total number of terms in the document). (# terms without stopwords)
    TF = (double) tInDoc / (double) docLen;

    // IDF(t) = log_e(Total number of documents / 1 + Number of documents with term t in it)
    IDF = log((double)totalDocs / (1 + (double)tInDocs));
    return TF * IDF;
}



// Get the TFIDFs for terms in the doc
map<string, double> GetDocTFIDFs(indri::collection::Repository& r, int totalDocs, const char* docno) {
    // Get documentinfo
    pair< int , map<string, TermInfo> > termInfo  = getDocInfo(r, docno);
    double maxTFIDF = 0;
    double minTFIDF = 0;

    map<string, double> TFIDFvector;

    for (map<string, TermInfo >::iterator it = termInfo.second.begin(); it != termInfo.second.end(); ++it)
    {
        // # number of doc with the term
        it->second.docCount = termInDocs(r, it->first);
        // calc TFIDF for term
        it->second.tf_idf = TFIDF(it->second.count, termInfo.first, totalDocs, it->second.docCount);
        // update max tf_idf for normalization
        if (it->second.tf_idf > maxTFIDF) {
            maxTFIDF = it->second.tf_idf;
        }
        // update min tf_idf for normalization
        if (it->second.tf_idf < minTFIDF) {
            minTFIDF = it->second.tf_idf;
        }
    }
    // Normalize TFIDFs
    for (map<string, TermInfo >::iterator it = termInfo.second.begin(); it != termInfo.second.end(); ++it) {
        TFIDFvector.insert(map<string, double>::value_type(it->first, (1-( (it->second.tf_idf - minTFIDF) / (maxTFIDF-minTFIDF) ) ) ) );
    }
    return TFIDFvector;
}


// calculates the R1 score
float R1(const vector<float>* Qscores) {
    float res = 0;
    for (vector<float>::const_iterator tf_idf = Qscores->begin(); tf_idf != Qscores->end(); ++tf_idf) {
        res += (1 - *tf_idf);
    }
    res = res / Qscores->size();
    return  res;
}

// calculates the R2 score, Qscores is the tf.idf
// ranks of the query-terms contined in a document
float R2(const vector<float>* Qscores) {
    float diff = 0;
    float res = 0;
    for (int i= 1; i < Qscores->size(); i++) {
     diff = (*Qscores)[i] - (*Qscores)[i-1];
     if (res < diff) {
         res = diff;
     }
    }
    return  1 - res;
}



// comare function for sorting into ranks by the R1 scores
bool pairR1Compare(const QueryDoc& firstE, const QueryDoc& secondE) {
    if ( firstE.R2_score != secondE.R2_score)
        return firstE.R1_score > secondE.R1_score;
    return (firstE.rank > secondE.rank);
}
// compare function for sorting into ranks by the R2 scores
bool pairR2Compare(const QueryDoc& firstE, const QueryDoc& secondE) {
    if (firstE.R2_score != secondE.R2_score) {
        return firstE.R2_score > secondE.R2_score;
    }
    return (firstE.rank > secondE.rank);
}
// compare function for sorting into ranks by the R1R2 ranks, and sort by
// original rank if a tie occurs
bool pairR1R2Compare(const QueryDoc& firstE , const QueryDoc& secondE) {
    if (firstE.R1R2_rank != secondE.R1R2_rank)
        return (firstE.R1R2_rank < secondE.R1R2_rank);
    return (firstE.rank < secondE.rank);
}




int print_document_vector(indri::collection::Repository& r,  int number) {
    indri::server::LocalQueryServer local(r);
    lemur::api::DOCID_T documentID = number;
    std::vector<lemur::api::DOCID_T> documentIDs;
    documentIDs.push_back(documentID);
    int termCount = 0;
    indri::server::QueryServerVectorsResponse* response = local.documentVectors(documentIDs);
    if ( response->getResults().size() ) {
        indri::api::DocumentVector* docVector = response->getResults()[0];
        for ( size_t i = 0; i < docVector->positions().size(); i++ ) {
            int position = docVector->positions()[i];
            const std::string& stem = docVector->stems()[position];
            if (position) {
                termCount++;
            }
        }
        delete docVector;
    }
    delete response;
    return termCount;
}


void print_repo_stats(indri::collection::Repository& r) {
    indri::server::LocalQueryServer local(r);
    UINT64 docCount = local.documentCount();

    int minLen = 999999999;
    int maxLen = 0;
    int terms = 0;
    int i = 1;
    int tempLen;

    cout << "Calculating Repository statistics, Please wait: \n";
    while ( i < docCount ) {
        tempLen = print_document_vector(r, i);
        terms += tempLen;
        if (minLen > tempLen) {
            minLen = tempLen;
        }
        if (maxLen < tempLen) {
            maxLen = tempLen;
        }
        i++;
    }
    double avgDocLen = terms / docCount;

    cout << "total " << terms << "\n";
    cout << "maxl " << maxLen << "\n";
    cout << "minl " << minLen << "\n";
    cout << "avgDocLen " << avgDocLen << "\n";
    cout << "docCount " << docCount << "\n";
}





int main(int argc, char* argv[]) {
    // get acces to the index
    indri::collection::Repository r;
    cout << argv[1] << "\n";
    r.openRead(argv[1]);
    indri::server::LocalQueryServer local(r);
    int totalDocs = local.documentCount();

    // check for the -s flag and print stats
    if ((strcmp(argv[2], "-S") ==0) || (strcmp(argv[2], "-s") ==0 )) {
        print_repo_stats(r);
        exit(1);
    }


    map<int, vector<QueryDoc>  > qRes = loadRes(r, argv[2]);
    map < string , vector<string> >  queriesMap = loadQueries();


    // get filenames for output and delete old files
    char fn1[100];
    strcat(strncpy(fn1, argv[3],sizeof(fn1)), "_R1_results.txt");
    remove(fn1);
    char fn2[100];
    strcat(strncpy(fn2, argv[3],sizeof(fn2)), "_R2_results.txt");
    remove(fn2);
    char fn3[100];
    strcat(strncpy(fn3, argv[3],sizeof(fn3)), "_R1R2_results.txt");
    remove(fn3);

    // open files for output in append mode
    ofstream r1file;
    ofstream r2file;
    ofstream r1r2file;
    r1file.open(fn1, ios_base::app);
    r2file.open(fn2, ios_base::app);
    r1r2file.open(fn3, ios_base::app);

    // For each QueryDoc
    for (map<int,  vector<QueryDoc>  > ::iterator Qresult = qRes.begin(); Qresult != qRes.end(); ++Qresult ) {
        // Get R1 for rank for Query
        // get first query
        int Qnum = Qresult->first;
        vector<QueryDoc> CurrrentQL = Qresult->second;
        int listSize = CurrrentQL.size();

        for (vector<QueryDoc>::iterator QL = CurrrentQL.begin(); QL != CurrrentQL.end(); ++QL) {
            QueryDoc& query = *QL;
            vector<float> Qscores;

            // get tf_idfs - <term - tf_idf>
            map<string, double> docvec = GetDocTFIDFs(r , totalDocs, query.docId.c_str());
            // < querynummer , queryterms>
            map < string , vector<string> > ::iterator it = queriesMap.find(int2str(Qnum));

            if (it != queriesMap.end()) {   // queryterms
                vector<string> vec = it->second;
                for (vector<string>::const_iterator its = vec.begin(); its != vec.end(); ++its) {

                    // get terms tf_idf
                    map<string, double>::iterator it2 = docvec.find(r.processTerm(*its));
                    if (it2 != docvec.end()) {
                        Qscores.push_back(it2->second);
                    } else {
                       // cout << "not found in document " <<  "\n" ;
                    }
                }
            }
            sort(Qscores.begin(), Qscores.end());
            query.R1_score = R1(&Qscores);
            // check if there is more than one term in the query
            if (it->second.size() > 1) {
                query.R2_score = R2(&Qscores);
            } else {
             query.R2_score = -1;
         }
     }

     // R1 sort
     sort(CurrrentQL.begin(), CurrrentQL.end(), pairR1Compare);

     int count = 1;
     for (vector<QueryDoc>::iterator QL = CurrrentQL.begin(); QL != CurrrentQL.end(); ++QL) {
        QueryDoc& query = *QL;
        query.R1_rank = count;
        r1file << Qnum << " Q0 " << query.docName << " " << query.R1_rank << " " << query.R1_score << " 2016 \n" ;
        count++;
    }

    // R2 sort
    sort(CurrrentQL.begin(), CurrrentQL.end(), pairR2Compare);

    count = 1;
    for (vector<QueryDoc>::iterator QL = CurrrentQL.begin(); QL != CurrrentQL.end(); ++QL) {
        QueryDoc& query = *QL;
        query.R2_rank = count;
        if (query.R2_score != -1) {
         query.R1R2_rank = round((count + query.R1_rank) / 2);
     } else {
        query.R1R2_rank =-1;
    }
    if (query.R2_score != -1) {
     r2file << Qnum << " Q0 " << query.docName << " " << query.R2_rank << " " << query.R2_score << " 2016 \n";
     count++;
    }
    
}
sort(CurrrentQL.begin(), CurrrentQL.end(), pairR1R2Compare);
count = 1;
for (vector<QueryDoc>::const_iterator QL = CurrrentQL.begin(); QL != CurrrentQL.end(); ++QL) {
    QueryDoc query = *QL;

    if (query.R1R2_rank != -1) {
        r1r2file << Qnum << " Q0 " << query.docName << " " << count << " " << listSize-count <<  " 2016  \n" ;
        count++;
    }

}
}
r1file.close();
r2file.close();
r1r2file.close();
return 0;
}

