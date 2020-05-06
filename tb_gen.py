#!/usr/bin/env python3

##############################################################################
# A simple VHDL test bench generator (for combinational logic)               #
##############################################################################
#
#########################
# Test case file format #   
#########################
#
# Line 1 contains a comma-separated list of input pins.
#
# Line 2 contains a comma-separated list of output pins.
#
# Lines 3 onwards contain test cases. Test cases comprise
# a comma-separated list of pin values, where input pins'
# values are given first, in the order specified in line 1,
# and output pins' values are given next, in the order
# specified on line 2. 
#
# Spaces and comment lines beginning with # are ignored.
#
# e.g.
#
#   # inputs
#   in1, in2, sel
#   # outputs
#   out1
#   # test cases
#   0,0,0,0
#   1,0,0,1 
#   0,1,0,0
#   0,1,1,1
#
##############################################################################


import argparse    


def indent_string(string: str, amount: int) -> str:
    """
    Indent a string by a given number of spaces.

    Parameters
    ----------
    string : str
        The string to indent.
    amount : int
        The number of spaces to indent by.

    Returns
    -------
    str
        The indented string.

    """
    return (" " * amount) + string


class CombTestBench:
    
    def __init__(self, entity_name: str, 
                 architecture_name: str, test_case_file: str):
        """
        Create a CombTestBench object.

        Parameters
        ----------
        entity_name : str
            The name of the entity to be tested.
        architecture_name : str
            The name of the architecture to use for the given entity.
        test_case_file : str
            The name of the file in which test cases are defined.
            
        """
        # save entity name and architecture name
        self.entity_name = entity_name
        self.architecture_name = architecture_name
        # process test case data
        with open(test_case_file, 'r') as f:
            # get lines from csv file
            content = f.readlines()
            # remove whitespace and comment lines
            content = [l.replace(" ", "").replace("\n", "") for l in content]
            content = [l for l in content if l[0] != "#"]
            # get input pins from first line
            self.input_pins = content[0].split(",")
            # get output pins from second line
            self.output_pins = content[1].split(",")
            # save other lines as test case data
            self.test_case_data = [
                dict(zip(self.input_pins + self.output_pins, l.split(",")))
                for l in content[2:]
            ]
    
    
    def generate(self, filename: str):
        """
        Generate a VHDL test bench and write it to the given file.

        Parameters
        ----------
        filename : str
            The name of the file to which the generated VHDL test bench
            will be written.

        Returns
        -------
        None.

        """
        # add header, including entity declaration and architecture header
        result = self.__HEADER.format(self.entity_name)
        # add internal signal declarations
        result += self.__generate_internal_signal_declarations()
        # add instantiation of unit under test
        result += "begin\n" + self.__generate_uut_instantiation()
        # begin test bench logic
        result += "\n" + self.__TB_LOGIC_HEADER
        # add test cases
        result += self.__generate_test_cases()
        # add overall test pass check and footer
        result += "\n" + self.__FOOTER
        # print result to console
        print(result)
        # write to given VHDL file
        with open(filename, 'w') as f:
            f.write(result)
    
        
    def __generate_internal_signal_declarations(self) -> str:
        result = indent_string("-- internal signal declarations\n", 4)
        result += indent_string("signal ", 4)
        result += ", ".join(["tb_" + p for p in self.input_pins]) + ", "
        result += ", ".join(["tb_" + p for p in self.output_pins])
        result += ": std_logic;\n"   
        return result
    
    
    def __generate_uut_instantiation(self) -> str:
        return self.__UUT_TEMPLATE.format(
            self.entity_name, 
            self.architecture_name,
            ", ".join(["tb_" + p for p in self.input_pins]),
            ", ".join(["tb_" + p for p in self.output_pins]))
    
    
    def __generate_test_cases(self) -> str:
        test_cases = [self.__generate_test_case(i) 
                      for i in range(len(self.test_case_data))]
        return "\n".join(test_cases)
            
    
    def __generate_test_case(self, num: int) -> str:
        lines = ["-- test case {0}".format(num)]
        lines += ["tb_{0} <= '{1}';".format(ip, self.test_case_data[num][ip])
                  for ip in self.input_pins]
        lines.append("wait for 10 ns;")
        lines.append("assert (" +  " and ".join(
            ["(tb_{0} = '{1}')".format(op, self.test_case_data[num][op])
             for op in self.output_pins]
        ) + ")")
        lines.append("report \"Test case {0} failed!\"".format(num))
        lines.append("severity error;")
        lines.append("if (" + " or ".join(
            ["(tb_{0} /= '{1}')".format(op, self.test_case_data[num][op])
             for op in self.output_pins]
        ) + ") then")
        lines.append(indent_string("fail_count := fail_count + 1;", 4))
        lines.append("end if;")
        return "\n".join([indent_string(l, 8) for l in lines]) + "\n"
            
    
    __HEADER = ("--------------------------------------------------------\n" +
              "-- Test bench for combinational entity {0}\n" +
              "-- Generated by tb_gen.py\n" +
              "--------------------------------------------------------\n\n"
              "library ieee;\n" +
              "use ieee.std_logic_1164.all;\n\n" +
              "-- test bench entity\n" +
              "entity {0}_tb is\n" +
              "end {0}_tb;\n\n" +
              "-- test bench architecture\n" +
              "architecture tb of {0}_tb is\n")
    
    __UUT_TEMPLATE =  (indent_string("-- instantiate unit under test\n", 4) +               
                     indent_string("UUT: entity work.{0}({1})\n", 4) +
                     indent_string("port map ({2}, {3});\n", 4))
    
    __TB_LOGIC_HEADER = (indent_string("-- test bench logic\n", 4) +
                       indent_string("process\n", 4) +
                       indent_string("-- test fail counter\n", 8) +
                       indent_string("variable fail_count: integer := 0;\n", 8) +
                       indent_string("begin\n", 4))
    
    __FOOTER = (indent_string("-- check if all tests passed\n", 8) +
		      indent_string("if (fail_count = 0) then\n", 8) +
			  indent_string("assert false report \"All tests passed!\"\n", 12) +
			  indent_string("severity note;\n", 12) +
		      indent_string("else\n", 8) +
			  indent_string("assert false report \"Testbench failed!\"\n", 12) +
			  indent_string("severity error;\n", 12) +
		      indent_string("end if;\n\n", 8) +
		      indent_string("wait;\n", 8) +
	          indent_string("end process;\n", 4) +
              "end tb;\n")
    
    
if __name__ == "__main__":
    # get entity name, architecture name, test case filename
    # and test bench VHDL filename from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("entity", help="the entity to test")
    parser.add_argument("architecture", 
                        help="the architecture to use for the given entity")
    parser.add_argument("test_case_file", 
                        help="the file in which test cases are defined")
    parser.add_argument("test_bench_vhdl_file", 
                        help="the file to which the generated VHDL test bench will be written")
    args = parser.parse_args()
    # create test bench
    tb = CombTestBench(args.entity, args.architecture, args.test_case_file)
    # generate test bench VHDL and write to file
    tb.generate(args.test_bench_vhdl_file)