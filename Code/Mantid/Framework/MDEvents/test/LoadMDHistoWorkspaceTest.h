#ifndef MANTID_MDEVENTS_LOADMDHISTOWORKSPACETEST_H_
#define MANTID_MDEVENTS_LOADMDHISTOWORKSPACETEST_H_

#include <cxxtest/TestSuite.h>
#include "MantidKernel/Timer.h"
#include "MantidKernel/System.h"
#include <iostream>
#include <iomanip>
#include <fstream>
#include "MantidMDEvents/LoadMDHistoWorkspace.h"
#include "MantidAPI/IMDHistoWorkspace.h"

using namespace Mantid;
using namespace Mantid::MDEvents;
using namespace Mantid::API;

/**
Helper type. Creates a test file, and also manages the resource to ensure that the file is closed and removed, no matter what the outcome of the test.
*/
class MDFileObject
{
public:

  /// Create a simple input file.
  MDFileObject(const std::string& filename, const size_t& size) : m_filename(filename)
  {
    m_file.open (filename.c_str());
    for(int i=1; i<size+1;++i)
    {
      m_file << i << "\t" << i+1 << std::endl;
    }
    m_file.close();
  }

  std::string getFileName() const
  {
    return m_filename;
  }

  /// Free up resources.
  ~MDFileObject()
  {
    m_file.close();
    if( remove( m_filename.c_str() ) != 0 )
      throw std::runtime_error("cannot remove " + m_filename);
  }

private:
  std::string m_filename;
  std::ofstream m_file;
  // Following methods keeps us from being able to put objects of this type on the heap.
  void *operator new(size_t);
  void *operator new[](size_t);
};

class LoadMDHistoWorkspaceTest : public CxxTest::TestSuite
{

private:

  /**
  Test helper method, builds a standard version of the algorithm, onto which properties can be overriden in indivdual tests.
  Helps make tests easy to read.
  */
  boost::shared_ptr<IAlgorithm> make_standard_algorithm(const MDFileObject& fileObject)
  {
    IAlgorithm_sptr alg = IAlgorithm_sptr(new LoadMDHistoWorkspace());
    alg->initialize();
    alg->setRethrows(true);
    alg->setPropertyValue("FileName", fileObject.getFileName());
    alg->setProperty("Dimensionality", 2);
    alg->setPropertyValue("Extents", "-1,1,-1,1");
    alg->setPropertyValue("NumberOfBins", "2,2");
    alg->setPropertyValue("Names", "A,B");
    alg->setPropertyValue("Units", "U1,U2");
    alg->setPropertyValue("OutputWorkspace", "test_workspace");
    return alg;
  }


public:
  // This pair of boilerplate methods prevent the suite being created statically
  // This means the constructor isn't called when running other tests
  static LoadMDHistoWorkspaceTest *createSuite() { return new LoadMDHistoWorkspaceTest(); }
  static void destroySuite( LoadMDHistoWorkspaceTest *suite ) { delete suite; }

  void test_Init()
  {
    LoadMDHistoWorkspace alg;
    TS_ASSERT_THROWS_NOTHING( alg.initialize() )
    TS_ASSERT( alg.isInitialized() )
  }

  void test_throws_if_dimensionality_less_than_one()
  {
    MDFileObject fileObject("test_file_for_load_md_histo_workspace_test_.txt", 2*2);
    IAlgorithm_sptr alg = make_standard_algorithm(fileObject);
    TS_ASSERT_THROWS(alg->setProperty("Dimensionality", 0), std::invalid_argument);
  }

  void test_throws_if_dimensionality_greater_than_nine()
  {
    MDFileObject fileObject("test_file_for_load_md_histo_workspace_test_.txt", 2*2);
    IAlgorithm_sptr alg = make_standard_algorithm(fileObject);
    TS_ASSERT_THROWS(alg->setProperty("Dimensionality", 10), std::invalid_argument);
  }

  void test_set_dimensionality()
  {
    MDFileObject fileObject("test_file_for_load_md_histo_workspace_test_.txt", 2*2);
    IAlgorithm_sptr alg = make_standard_algorithm(fileObject);
    TS_ASSERT_THROWS_NOTHING(alg->setProperty("Dimensionality", 9));
  }

  void test_throws_without_filename()
  {
    MDFileObject fileObject("test_file_for_load_md_histo_workspace_test_.txt", 2*2);
    IAlgorithm_sptr alg = make_standard_algorithm(fileObject);
    TS_ASSERT_THROWS(alg->setProperty("Filename", ""), std::invalid_argument);
  }

  void test_throws_with_non_existant_filename()
  {
    MDFileObject fileObject("test_file_for_load_md_histo_workspace_test_.txt", 2*2);
    IAlgorithm_sptr alg = make_standard_algorithm(fileObject);
    TS_ASSERT_THROWS(alg->setProperty("Filename", "does_not_exist.txt"), std::invalid_argument);
  }

  void test_throws_when_wrong_number_of_extent_entries()
  {
    MDFileObject fileObject("test_file_for_load_md_histo_workspace_test_.txt", 2*2);
    IAlgorithm_sptr alg = make_standard_algorithm(fileObject);
    alg->setPropertyValue("Extents","1,-1"); //Extents only provided for 1Dimension!
    TS_ASSERT_THROWS(alg->execute(), std::invalid_argument);
  }

  void test_throws_when_wrong_number_of_name_entries()
  {
    MDFileObject fileObject("test_file_for_load_md_histo_workspace_test_.txt", 2*2);
    IAlgorithm_sptr alg = make_standard_algorithm(fileObject);
    alg->setPropertyValue("Names","A"); // Names only provided for 1Dimension!
    TS_ASSERT_THROWS(alg->execute(), std::invalid_argument);
  }

  void test_throws_when_wrong_number_of_unit_entries()
  {
    MDFileObject fileObject("test_file_for_load_md_histo_workspace_test_.txt", 2*2);
    IAlgorithm_sptr alg = make_standard_algorithm(fileObject);
    alg->setPropertyValue("Units","U1"); // Units only provided for 1Dimension!
    TS_ASSERT_THROWS(alg->execute(), std::invalid_argument);
  }

  void test_throws_when_wrong_number_of_bin_entries()
  {
    MDFileObject fileObject("test_file_for_load_md_histo_workspace_test_.txt", 2*2);
    IAlgorithm_sptr alg = make_standard_algorithm(fileObject);
    alg->setPropertyValue("Names","2"); // bin numbers only provided for 1Dimension!
    TS_ASSERT_THROWS(alg->execute(), std::invalid_argument);
  }

  void test_throws_when_dimensionality_num_bins_and_file_size_do_not_match()
  {
    MDFileObject fileObject("test_file_for_load_md_histo_workspace_test_.txt", 3*3); //bin size set to 3, so 3*3*2, entries will be in the file! i.e file corrsponds to 2D md workspace.
    IAlgorithm_sptr alg = make_standard_algorithm(fileObject);
    alg->setPropertyValue("Extents", "-1,1,-1,1,-1,1");
    alg->setPropertyValue("NumberOfBins", "3,3,3"); //but the nubmer of bins has been set to 3!
    alg->setPropertyValue("Names", "A,B,C");
    alg->setPropertyValue("Units", "U1,U2,U3");
    alg->setProperty("Dimensionality", 3); //but dimensionality has been set to 3 also!
    TS_ASSERT_THROWS(alg->execute(), std::invalid_argument);
  }

  /// Test execution with as specific output dimensionality required.
  void test_executes_2D()
  {
    MDFileObject fileObject("test_file_for_load_md_histo_workspace_test_.txt", 2*2);
    IAlgorithm_sptr alg = IAlgorithm_sptr(new LoadMDHistoWorkspace());
    alg->initialize();
    alg->setPropertyValue("FileName", fileObject.getFileName());
    alg->setProperty("Dimensionality", 2);
    alg->setPropertyValue("Extents", "-1,1,-1,1");
    alg->setPropertyValue("NumberOfBins", "2,2");
    alg->setPropertyValue("Names", "A,B");
    alg->setPropertyValue("Units", "U1,U2");
    alg->setPropertyValue("OutputWorkspace", "test_workspace");
    alg->setRethrows(true);
    alg->execute();
    TS_ASSERT(alg->isExecuted());

    // Check execution
    AnalysisDataServiceImpl& ADS = AnalysisDataService::Instance();
    TS_ASSERT(ADS.doesExist("test_workspace"));
    
    // Check the workspace
    IMDHistoWorkspace_sptr outWs = boost::dynamic_pointer_cast<IMDHistoWorkspace>(ADS.retrieve("test_workspace"));
    TS_ASSERT(outWs != NULL);

    // Check the dimensionality
    TS_ASSERT_EQUALS(2, outWs->getNumDims());
    auto dim1 = outWs->getDimension(0);
    auto dim2 = outWs->getDimension(1);

    TS_ASSERT_EQUALS("A", dim1->getName());
    TS_ASSERT_EQUALS("A", dim1->getDimensionId());
    TS_ASSERT_EQUALS("U1", dim1->getUnits());
    TS_ASSERT_EQUALS(1, dim1->getMaximum());
    TS_ASSERT_EQUALS(-1, dim1->getMinimum());
    TS_ASSERT_EQUALS(2, dim1->getNBins());

    TS_ASSERT_EQUALS("B", dim2->getName()); 
    TS_ASSERT_EQUALS("B", dim2->getDimensionId());
    TS_ASSERT_EQUALS("U2", dim2->getUnits());
    TS_ASSERT_EQUALS(1, dim2->getMaximum());
    TS_ASSERT_EQUALS(-1, dim2->getMinimum());
    TS_ASSERT_EQUALS(2, dim2->getNBins());

    // Check the data
    double* signals = outWs->getSignalArray();
    TS_ASSERT_DELTA(1, signals[0], 0.0001); // Check the first signal value
    TS_ASSERT_DELTA(2, signals[1], 0.0001); // Check the second signal value
    double* errorsSQ = outWs->getErrorSquaredArray();
    TS_ASSERT_DELTA(2*2, errorsSQ[0], 0.0001); // Check the first error value
    TS_ASSERT_DELTA(3*3, errorsSQ[1], 0.0001); // Check the second error value

    ADS.remove("test_workspace");
  }

  /// Test execution with a different (from above) output dimensionality required.
  void test_executes_3D()
  {
    MDFileObject fileObject("test_file_for_load_md_histo_workspace_test_.txt", 2*2*2);
    IAlgorithm_sptr alg = IAlgorithm_sptr(new LoadMDHistoWorkspace());
    alg->initialize();
    alg->setPropertyValue("FileName", fileObject.getFileName());
    alg->setProperty("Dimensionality", 3);
    alg->setPropertyValue("Extents", "-1,1,-1,1,-1,1");
    alg->setPropertyValue("NumberOfBins", "2,2,2");
    alg->setPropertyValue("Names", "A,B,C");
    alg->setPropertyValue("Units", "U1,U2,U3");
    alg->setPropertyValue("OutputWorkspace", "test_workspace");
    alg->setRethrows(true);
    alg->execute();
    TS_ASSERT(alg->isExecuted());

    // Check execution
    AnalysisDataServiceImpl& ADS = AnalysisDataService::Instance();
    TS_ASSERT(ADS.doesExist("test_workspace"));
    
    // Check the workspace
    IMDHistoWorkspace_sptr outWs = boost::dynamic_pointer_cast<IMDHistoWorkspace>(ADS.retrieve("test_workspace"));
    TS_ASSERT(outWs != NULL);

    // Check the dimensionality
    TS_ASSERT_EQUALS(3, outWs->getNumDims());

    ADS.remove("test_workspace");
  }
  
  
};


#endif /* MANTID_MDEVENTS_LOADMDHISTOWORKSPACETEST_H_ */