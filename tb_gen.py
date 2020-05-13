#!/usr/bin/env python3

##############################################################################
# A VHDL test bench generator for combinational and sequential logic         #
##############################################################################

import json
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


class TestBench:
            
    def load(self, test_bench_file: str):
        """
        Load test bench details from a JSON test case file.

        Parameters
        ----------
        test_bench_file : str
            The JSON file in which test case details are stored.

        Returns
        -------
        None.

        """
        # parse JSON file, saving result to dict
        with open(test_bench_file, 'r') as f:
            self.data = json.load(f)
            # add correct quotes to test case pin values - single for
            # std_logic (single bit), double for std_logic_vector (bus)
            self.__quote_pin_values()
            # convert clock pin to same format as input and output pins,
            # giving it a single bit width
            self.data["clock_pin"] = { 
                self.data["clock_pin"]: None 
            } if self.data["clocked"] else {}
    
    
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
        result = self.__HEADER.format(
            self.data["library"],
            self.data["entity"],
            self.data["architecture"]
        )
        # add clock wait procedure if entity is clocked
        if self.data["clocked"]:
            result += self.__CLK_WAIT_PRCD + "\n"
        # add internal signal declarations
        result += self.__generate_internal_signal_declarations()
        # add instantiation of unit under test
        result += "begin\n" + self.__generate_uut_instantiation()
        # add clock process if entity is clocked
        if self.data["clocked"]:
            result += "\n" + self.__generate_clock_process()
        # begin test bench process
        result += "\n" + self.__TB_PROC_HEADER
        # add test cases
        result += self.__generate_test_cases()
        # add overall test pass check and footer
        result += "\n" + self.__FOOTER
        # print result to console
        #print(result)
        # write to given VHDL file
        print("Writing test bench VHDL to " + filename)
        print("Testbench entity is called '" + self.data["entity"]  + "_tb'")
        with open(filename, 'w') as f:
            f.write(result)


    def __quote_pin_values(self):
        # concatenate input and output pin dicts
        pins = dict(self.data["input_pins"], 
                    **self.data["output_pins"])
        # for every test case
        for t in self.data["test_cases"]:
            # for each pin
            for p in pins.keys():
                # give value single or double quotes based on pin bus width
                t[p] = f'"{t[p]}"' if pins[p] else f"'{t[p]}'"
    
        
    def __generate_internal_signal_declarations(self) -> str:
        # add comment line
        result = indent_string("-- internal signal declarations\n", 4)
        # for each set of pins (input, clock and output)
        for s in [self.data["input_pins"],
                  self.data["clock_pin"],
                  self.data["output_pins"]]:
            # for each pin and width (if multi-bit bus) pair
            for p, w in s.items():
                # vector type if width was given
                t = f"std_logic_vector({w-1} downto 0)" if w else "std_logic"
                # generate and add signal declaration
                result += indent_string("signal tb_" + p + ": " + t + ";\n", 4)
        # return block of signal declarations
        return result
    
    
    def __generate_uut_instantiation(self) -> str:
        # generic map empty by default
        generic_map = ""
        # if generic arguments were specified
        if self.data["generic_params"]:
            # generate generic map
            generic_map += indent_string("generic map (\n", 11)
            generic_map += ",\n".join([
                indent_string(f"{param} => {val}", 15)
                for param, val in
                self.data["generic_params"].items()
            ])
            generic_map += "\n" + indent_string(")\n", 11)
        # format unit under test instantiation template
        result = self.__UUT_TEMPLATE.format(
            self.data["library"],
            self.data["entity"],
            self.data["architecture"],
            generic_map,
            self.__generate_port_map(self.data["input_pins"]) +
            self.__generate_port_map(self.data["clock_pin"]) +
            self.__generate_port_map(self.data["output_pins"], True)
        )
        return result
    
    
    def __generate_port_map(self, pins: dict, end: bool = False) -> str:
        # generate port map for pins, mapping entity port to testbench signal
        result =  ",\n".join([
            indent_string(f'{p} => {"tb_" + p}', 15)
            for p in pins.keys()
        ])
        if len(result) > 0 and not end:
            result += ",\n"
        return result
    
    
    def __generate_clock_process(self) -> str:
        return self.__CLK_PROC_TEMPLATE.format(
            next(iter(self.data["clock_pin"])),
            self.data["clock_period"] // 2
        )
    
    
    def __generate_test_cases(self) -> str:
        # generate vhdl test case for each given test case
        test_cases = [self.__generate_test_case(i) 
                      for i in range(len(self.data["test_cases"]))]
        return "\n".join(test_cases)
            
    
    def __generate_test_case(self, num: int) -> str:
        # add comment
        lines = [f"-- test case {num}"]
        # assign values to input pins
        lines += [
            "tb_{0} <= {1};".format(ip, self.data["test_cases"][num][ip])
            for ip in self.data["input_pins"]
        ]
        # wait time
        lines.append(
            self.__generate_wait_statement(
                self.data["test_cases"][num]["_wait"]
            )
        )
        # assert output values are as expected
        lines.append("assert (" +  " and ".join([
            "(tb_{0} = {1})".format(op, self.data["test_cases"][num][op])
            for op in self.data["output_pins"]
        ]) + ")")
        lines.append(f'report "Test case {num} failed!"')
        lines.append("severity error;")
        # increment fail count if test failed
        lines.append("if (" + " or ".join([
            "(tb_{0} /= {1})".format(op, self.data["test_cases"][num][op])
            for op in self.data["output_pins"]
        ]) + ") then")
        lines.append(indent_string("fail_count := fail_count + 1;", 4))
        lines.append("end if;")
        # indent lines of code 8 spaces and join with newlines
        return "\n".join([indent_string(l, 8) for l in lines]) + "\n"
    

    def __generate_wait_statement(self, code: int) -> str:
        if code > 0:
            return "wait_until_clk_edges({0}, {1}, {2});".format(
                "tb_" + next(iter(self.data["clock_pin"])),
                code,
                "true"
            )
        elif code < 0:
            return "wait_until_clk_edges({0}, {1}, {2});".format(
                "tb_" + next(iter(self.data["clock_pin"])),
                -code,
                "false"
            )
        else:
            return "wait for 10 ns;"
            
    
    __HEADER = ("--------------------------------------------------------\n" +
                "-- Test bench for entity {0}.{1}({2})\n" +
                "-- Generated by tb_gen.py\n" +
                "--------------------------------------------------------\n\n"
                "library ieee;\n" +
                "use ieee.std_logic_1164.all;\n" +
                "library {0};\n\n" +
                "-- test bench entity\n" +
                "entity {1}_tb is\n" +
                "end {1}_tb;\n\n" +
                "-- test bench architecture\n" +
                "architecture tb of {1}_tb is\n")
    
    __CLK_WAIT_PRCD = (indent_string("-- procedure to wait for a number of " +
                                     "rising or falling clock edges\n", 4) +
                       indent_string("procedure wait_until_clk_edges " + 
                                     "(signal clk: in std_logic; " + 
                                     "n: in positive; rising: in boolean) is\n", 4) +
                       indent_string("begin\n", 4) +
                       indent_string("if rising then\n", 8) +
                       indent_string("for i in 1 to n loop\n", 12) +
                       indent_string("wait until rising_edge(clk);\n", 16) +
                       indent_string("end loop;\n", 12) +
                       indent_string("else\n", 8) +
                       indent_string("for i in 1 to n loop\n", 12) +
                       indent_string("wait until falling_edge(clk);\n", 16) +
                       indent_string("end loop;\n", 12) +
                       indent_string("end if;\n", 8) + 
                       indent_string("end procedure;\n", 4))
    
    __UUT_TEMPLATE =  (indent_string("-- instantiate unit under test\n", 4) +               
                       indent_string("E_UUT: entity {0}.{1}({2})\n", 4) +
                       "{3}"+
                       indent_string("port map (\n", 11) +
                       "{4}\n" +
                       indent_string(");\n", 11))
    
    __CLK_PROC_TEMPLATE = (indent_string("-- clock process\n", 4) +
                           indent_string("process\n", 4) +
                           indent_string("begin\n", 4) +
                           indent_string("tb_{0} <= '0';\n", 8) +
                           indent_string("wait for {1} ns;\n", 8) +
                           indent_string("tb_{0} <= '1';\n", 8) +
                           indent_string("wait for {1} ns;\n", 8) +
                           indent_string("end process;\n", 4))
    
    __TB_PROC_HEADER = (indent_string("-- test bench process\n", 4) +
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
    # get test case filename and test bench VHDL filename 
    # from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("test_case_file", 
                        help="the JSON file in which test cases are defined")
    parser.add_argument("test_bench_vhdl_file", 
                        help="the file to which the generated VHDL test bench will be written")
    args = parser.parse_args()
    # create test bench
    tb = TestBench()
    # load test case file
    tb.load(args.test_case_file)
    # generate test bench VHDL and write to file
    tb.generate(args.test_bench_vhdl_file)
