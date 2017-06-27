from mantid.simpleapi import FunctionFactory

class FunctionWrapper:
# Wrapper class for Fitting Function 
  def __init__ (self, name, **kwargs):
    if not isinstance(name, str):
       self.fun = name
    else:
       self.fun = FunctionFactory.createFunction(name)
    
       # Deal with attributes first
#       for key in kwargs:
#          if(self.fun.hasAttribute(key)):
#              self.fun.storeAttributeValue(key, kwargs[key])
            
       # Then deal with parameters        
       for key in kwargs:
          self.fun.setParameter(key, kwargs[key])
             
  def __getitem__ (self, name):
      return self.fun.getParameterValue(name)
      
  def __setitem__ (self, name, value):
      self.fun.setParameter(name, value)
      
  def __str__ (self):
      return self.fun.__str__()
                 
  def __add__ (self, other):
      if(isinstance(self,CompositeFunctionWrapper)):
        sum = self
        return sum.fun.add(other.fun)
      else:
        return CompositeFunctionWrapper(self,other)
        
  def tie (self, *args, **kwargs):
    for a in args:
        if isinstance(a, dict):
          for key in a:
            self.fun.tie(key, str(a[key]), False)

    for key in kwargs:
        self.fun.tie(key, str(kwargs[key]), False)
        
  def fix(self, name):
      self.fun.fix(name)
      
  def fixAllParameters(self):
       for i in range(0, self.fun.numParams()):
          self.fix(self.getParameterName(i))
      
  def untie(self, name):
      self.fun.untie(name)
      
  def untieAllParameters(self):
       for i in range(0, self.fun.numParams()):
          self.untie(self.getParameterName(i))
          
  def constrain(self, expressions):
      self.fun.constrain( expressions, False )
      
  def unconstrain(self, name):
      self.fun.unconstrain(name)
      
  def free(self, name):
  # Free parameter from tie or constraint
      self.fun.untie(name)
      self.fun.unconstrain(name)
      
  def getParameterName(self, index):
  # Get the name of the parameter of given index
      return self.fun.getParamName(index)
      
  def getFunction(self):
      return self.fun
      
class CompositeFunctionWrapper(FunctionWrapper):
# Wrapper class for Composite Fitting Function
    def __init__ (self, *args):
       if hasattr(args[0],'nFunctions'):
          # We have a composite function to wrap
          self.fun = args[0]
       else:
          self.fun = FunctionFactory.createFunction("CompositeFunction")
   
          #Add the functions
          for a in args:
             self.fun.add(a.fun)      
      
    def getParameter(self, name):
    # get parameter of specified name
        return self.fun.getParameterValue(name)
        
    def getCompositeParameterName(self, name, index):
    # get composite parameter name of parameter of 
    # given name of member function of given index
        return "f"+str(index)+"."+name

    def __getitem__ (self, nameorindex):
    # get function of specified index or parameter of specified name
        item = self.fun.__getitem__(nameorindex)
        if( isinstance(item, float)):
           return  item
        elif( hasattr(item, 'nFunctions')):
           # item is a CompositeFunction
           return CompositeFunctionWrapper(item)
        else:           
           return FunctionWrapper(item)

    def __setitem__ (self, name, newValue):
    # set parameter of specified name
        self.fun.__setitem__(name, newValue)
                    
    def __iadd__ (self, other):
       self.fun.add(other.fun)
       return self
       
    def __delitem__ (self, index):
       self.fun.__delitem__(index)
       
    def __len__ (self):
       return self.fun.__len__()
       
    def __iter__ (self):
       return self
       
    def tieAll (self, name):
    # For each member function, tie the parameter of the given name 
    # to the parameter of that name in the first member function.
    # The named parameter must occur in all the member functions.
       expr = self.getCompositeParameterName(name, 0)
       self.tie({self.getCompositeParameterName(name, i): expr for i in range(1,self.__len__()) }) 
          
    def fixAll (self, name):
    # Fix all parameters with the given local name.
    # Every member function must have a parameter of this name.
       for i in range(0, self.__len__()):
          self[i].fix(name)
          
    def constrainAll (self, expressions):
    # Constrain all parameters according local names in expressions.
       for i in range(0, self.__len__()):
          if( isinstance( self[i], CompositeFunctionWrapper )):
             self[i].constrainAll(expressions)
          else:
             try:
                self[i].constrain(expressions)
             except:
                pass
          
    def untieAll (self, name):
    # Untie all parameters with the given local name.
    # Every member function must have a parameter of this name.
       for i in range(0, self.__len__()):
          self[i].untie(name)
        
      