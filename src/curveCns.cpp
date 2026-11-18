/*

MGEAR is under the terms of the MIT License

Copyright (c) 2016 Jeremie Passerin, Miquel Campos

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Author:     Jeremie Passerin      geerem@hotmail.com  www.jeremiepasserin.com
Author:     Miquel Campos         hello@miquel-campos.com  www.miquel-campos.com
Date:       2016 / 10 / 10

*/
/////////////////////////////////////////////////
// INCLUDE
/////////////////////////////////////////////////
#include "mgear_solvers.h"

/////////////////////////////////////////////////
// GLOBAL
/////////////////////////////////////////////////
MTypeId mgear_curveCns::id(0x0011FEC2);
MObject mgear_curveCns::inputs;

/////////////////////////////////////////////////
// METHODS
/////////////////////////////////////////////////

mgear_curveCns::SchedulingType mgear_curveCns::schedulingType() const
{
	return kParallel;
}

// CREATOR ======================================
void* mgear_curveCns::creator() { return new mgear_curveCns; }

// INIT =========================================
MStatus mgear_curveCns::initialize()
{
	MFnMatrixAttribute mAttr;
	MStatus stat;

	// INPUTS
	inputs = mAttr.create( "inputs", "inputs" );
	mAttr.setStorable(true);
    mAttr.setReadable(false);
    mAttr.setArray(true);
    mAttr.setIndexMatters(false);
	stat = addAttribute( inputs );
		if (!stat) {stat.perror("addAttribute"); return stat;}

	// CONNECTIONS
	stat = attributeAffects( inputs, outputGeom );
		if (!stat) { stat.perror("attributeAffects"); return stat;}

    return MS::kSuccess;
}

// COMPUTE ======================================
MStatus mgear_curveCns::deform( MDataBlock& data, MItGeometry& iter, const MMatrix &mat, unsigned int /* mIndex */ )
{
    MStatus returnStatus;

	MArrayDataHandle adh = data.inputArrayValue( inputs );
	int deformer_count = adh.elementCount( &returnStatus );

	// Process
	while (! iter.isDone()){
		if (iter.index() < deformer_count){
			adh.jumpToElement(iter.index());
			MTransformationMatrix m(adh.inputValue().asMatrix() * mat.inverse());
			MVector v = m.getTranslation(MSpace::kWorld, &returnStatus );
			MPoint pt(v);
			iter.setPosition(pt);
		}
		iter.next();
	}

    return MS::kSuccess;
}

