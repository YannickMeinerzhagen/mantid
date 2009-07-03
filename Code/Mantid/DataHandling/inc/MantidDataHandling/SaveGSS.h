#ifndef DATAHANDING_SAVEGSS_H_
#define DATAHANDING_SAVEGSS_H_

//---------------------------------------------------
// Includes
//---------------------------------------------------
#include "MantidAPI/Algorithm.h"

namespace Mantid
{

namespace DataHandling
{
/**
     Saves a focused data set
     into a three column GSAS format containing X_i, Y_i*step, and E_I*step. Exclusively for
     the crystallography package GSAS and data needs to be in time-of-flight
     For data where the focusing routine has generated several spectra (for example, multi-bank instruments),
     the option is provided for saving all spectra into a single file, separated by headers, or into
     several files that will be named "workspaceName_"+spectra_number.

     Required properties:
     <UL>
     <LI> InputWorkspace - The workspace name to save. </LI>
     <LI> Filename - The filename for output </LI>
     <LI> SplitFiles- Option for splitting into N files for workspace with N-spectra</UL>

     @author Laurent Chapon, ISIS Facility, Rutherford Appleton Laboratory
     @date 04/03/2009

     Copyright &copy; 2009 STFC Rutherford Appleton Laboratories

     This file is part of Mantid.

     Mantid is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 3 of the License, or
     (at your option) any later version.

     Mantid is distributed in the hope that it will be useful,
     but WITHOUT ANY WARRANTY; without even the implied warranty of
     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
     GNU General Public License for more details.

     You should have received a copy of the GNU General Public License
     along with this program.  If not, see <http://www.gnu.org/licenses/>.

     File change history is stored at: <https://svn.mantidproject.org/mantid/trunk/Code/Mantid>
     Code Documentation is available at: <http://doxygen.mantidproject.org>
  */
class DLLExport SaveGSS : public Mantid::API::Algorithm
{
public:
  /// (Empty) Constructor
  SaveGSS() : Mantid::API::Algorithm(){}
  /// Virtual destructor
  virtual ~SaveGSS() {}
  /// Algorithm's name
  virtual const std::string name() const { return "SaveGSS"; }
  /// Algorithm's version
  virtual const int version() const { return (1); }
  /// Algorithm's category for identification
  virtual const std::string category() const { return "Diffraction"; }
  ///
private:
  /// Initialisation code
  void init();
  ///Execution code
  void exec();
  ///Write the header information
  void writeHeaders(std::ostream& os,API::MatrixWorkspace_const_sptr& workspace) const;
};

}

}

#endif //DATAHANDING_SAVEGSS_H_
