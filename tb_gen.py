#!/usr/bin/env python3

##############################################################################
# A simple VHDL test bench generator (for combinational logic)               #
##############################################################################
#
#########################
# Test case file format #   
#########################
#
# Spaces and comment lines beginning with # are ignored.
#
# Line 1 contains the name of the entity to test.
#
# Line 2 contains the name of the architecture to use for the given entity.
#
# Line 3 contains a list of generic parameter names, separated by commas. 
# If no generic arguments are needed, write None in this line.
#
# Line 4 contains a list of generic arguments, separated by commas, 
# in the same order as the previously given generic parameter names.
# If no generic arguments are needed, write None in this line.
#
# Line 5 contains a comma-separated list of input pins. If the pin is a
# multi-bit bus, specify its length in parentheses after its name.
#
# Line 6 contains a comma-separated list of output pins. If the pin is a
# multi-bit bus, specify its length in parentheses after its name.
#
# Lines 7 onwards contain test cases. Test cases comprise
# a comma-separated list of pin values, where input pins'
# values are given first, in the order specified in line 5,
# and output pins' values are given next, in the order
# specified on line 6. Pin values must be surrounded by the 
# correct style of quotes for their data type, i.e. single 
# quotes for std_logic and double quotes for std_logic_vector.
#
#
# e.g.
#
#   # entity
#   mux2to1
#   # architecture
#   rtl
#   # generic parameter names
#   g_BUS_WIDTH
#   # generic arguments
#   2
#   # inputs
#   in1(2), in2(2), sel
#   # outputs
#   out1(2)
#   # test cases
#   "01","00",'0',"01"
#   "10","00",'0',"10"
#   "00","11",'0',"00"
#   "00","11",'1',"11"
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
            
    def load(self, test_case_file: str):
        """
        Load test bench details from test case file.

        Parameters
        ----------
        test_case_file : str
            The file in which test case details are stored.

        Returns
        -------
        None.

        """
        # open test case file
        with open(test_case_file, 'r') as f:
            # read lines from file
            content = f.readlines()
            # remove whitespace, newlines and comment lines
            content = [l.replace(" ", "").replace("\n", "") for l in content]
            content = [l for l in content if l[0] != "#"]
            # get entity name from first line
            self.entity_name = content[0]
            # notify user of test bench entity name
            print("Test bench entity will be called '" + 
                  self.entity_name + "_tb'")
            # get architecture name from second line
            self.architecture_name = content[1]
            # get generic parameters and arguments from third and fourth lines
            self.generic_arguments = self.__parse_generic_arguments(
                content[2].split(","),
                content[3].split(",")
            )
            # get input and output pins from fifth and sixth lines
            input_pins = content[4].split(",")
            self.input_pins = self.__parse_pins(input_pins)
            output_pins = content[5].split(",")
            self.output_pins = self.__parse_pins(output_pins)
            # save other lines as test case data
            self.test_case_data = [
                dict(zip(list(self.input_pins.keys()) + 
                         list(self.output_pins.keys()), l.split(",")))
                for l in content[6:]
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
        #print(result)
        # write to given VHDL file
        print("Writing test bench VHDL to " + filename)
        with open(filename, 'w') as f:
            f.write(result)
            
            
    def __parse_generic_arguments(self, params: list, values: list) -> dict:
        # no params if 'none' is part of line
        if [p.lower() for p in params].count("none"):
            params = None
        # no params if 'none' is part of line
        if [v.lower() for v in values].count("none"):
            values = None
        # return generic argument dict if params and values were present
        return dict(zip(params, values)) if params and values else None
        
            
    def __parse_pins(self, pins: list) -> dict:
        # dictionary which stores pin name and bus width if multi-bit bus
        result = {}
        # for each pin declaration
        for p in pins:
            # find parentheses meaning multi-bit bus
            paren = p.find("(")
            if paren >= 0:
                # save pin name and bus width if width was given
                result[p[:paren]] = int(p[paren+1:-1])
            else:
                # otherwise save pin name and None
                result[p] = None
        return result        
    
        
    def __generate_internal_signal_declarations(self) -> str:
        # add comment line
        result = indent_string("-- internal signal declarations\n", 4)
        # for each set of pins (input and output)
        pin_sets = [self.input_pins, self.output_pins]
        for s in pin_sets:
            # for each pin and width (if multi-bit bus) pair
            for p, w in s.items():
                # vector type if width was given
                t = "std_logic_vector({0} downto 0)".format(w-1) if w else "std_logic"
                # generate and add signal declaration
                result += indent_string("signal tb_" + p + ": " + t + ";\n", 4)
        # return block of signal declarations
        return result
    
    
    def __generate_uut_instantiation(self) -> str:
        # generic map empty by default
        generic_map = ""
        # if generic arguments were specified
        if self.generic_arguments:
            # generate generic map
            generic_map += "generic map ("
            generic_map += ", ".join([
                "{0} => {1}".format(param, val)
                for param, val in self.generic_arguments.items()
            ])
            generic_map += ")\n"
        # format unit under test instantiation template
        result = self.__UUT_TEMPLATE.format(
            self.entity_name, 
            self.architecture_name,
            generic_map,
            ", ".join(["tb_" + p for p in self.input_pins]),
            ", ".join(["tb_" + p for p in self.output_pins]))
        return result
    
    
    def __generate_test_cases(self) -> str:
        # generate vhdl test case for each given test case
        test_cases = [self.__generate_test_case(i) 
                      for i in range(len(self.test_case_data))]
        return "\n".join(test_cases)
            
    
    def __generate_test_case(self, num: int) -> str:
        # add comment
        lines = ["-- test case {0}".format(num)]
        # assign values to input pins
        lines += ["tb_{0} <= {1};".format(ip, self.test_case_data[num][ip])
                  for ip in self.input_pins]
        # wait time
        lines.append("wait for 10 ns;")
        # assert output values are as expected
        lines.append("assert (" +  " and ".join(
            ["(tb_{0} = {1})".format(op, self.test_case_data[num][op])
             for op in self.output_pins]
        ) + ")")
        lines.append("report \"Test case {0} failed!\"".format(num))
        lines.append("severity error;")
        # increment fail count if test failed
        lines.append("if (" + " or ".join(
            ["(tb_{0} /= {1})".format(op, self.test_case_data[num][op])
             for op in self.output_pins]
        ) + ") then")
        lines.append(indent_string("fail_count := fail_count + 1;", 4))
        lines.append("end if;")
        # indent lines of code 8 spaces and join with newlines
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
                       indent_string("E_UUT: entity work.{0}({1})\n", 4) +
                       indent_string("{2}", 11) +
                       indent_string("port map ({3}, {4});\n", 11))
    
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
    parser.add_argument("test_case_file", 
                        help="the file in which test cases are defined")
    parser.add_argument("test_bench_vhdl_file", 
                        help="the file to which the generated VHDL test bench will be written")
    args = parser.parse_args()
    # create test bench
    tb = CombTestBench()
    # load test case file
    tb.load(args.test_case_file)
    # generate test bench VHDL and write to file
    tb.generate(args.test_bench_vhdl_file)