
class Function:
                                                # DATA ACCESS
                                                # -----------
                                                # Bit access
    # Physical discrete inputs

    ReadDiscreteInputs                  = 0x02  #  2

    # Internal bits or physical coils

    ReadCoils                           = 0x01  #  1
    WriteSingleCoil                     = 0x05 	#  5
    WriteMultipleCoils                  = 0x0F  # 15

                                                # 16-bit access
    # Physical Input Registers

    ReadInputRegister                   = 0x04 	#  4

    # Internal Registers or Physical Output Registers

    ReadMultipleHoldingRegisters        = 0x03  #  3
    WriteSingleHoldingRegister          = 0x06  #  6 	
    WriteMultipleHoldingRegisters       = 0x10  # 16
    ReadWriteMultipleRegisters          = 0x17  # 23
    MaskWriteRegister                   = 0x16  # 22 	
    ReadFIFOQueue                       = 0x18  # 24

                                                # File Record Access

    ReadFileRecord                      = 0x14  # 20 	
    WriteFileRecord                     = 0x15  # 21

                                                # DIAGNOSTICS
                                                # -----------

    ReadExceptionStatus                 = 0x07  #  7 	serial only
    Diagnostic                          = 0x08  #  8 	serial only
    GetComEventCounter                  = 0x0B  # 11 	serial only
    GetComEventLog                      = 0x0C  # 12 	serial only
    ReportSlaveID                       = 0x11  # 17 	serial only
    ReadDeviceIdentification            = 0x2B  # 43 	

                                                # OTHER
                                                # -----

    EncapsulatedInterfaceTransport      = 0x2B  # 43 


class Exception:
    Mask                                = 0x80
                                                # EXCEPTION
                                                # ---------
    #IllegalFunction                     = 0x01  #  1
    #IllegalDataAddress                  = 0x02  #  2
    IllegalDataValue                    = 0x03  #  3
    SlaveDeviceFailure                  = 0x04  #  4
    Acknowledge                         = 0x05  #  5
    ServerDeviceBusy                    = 0x06  #  6
    NegativeAcknowledge                 = 0x07  #  7
    MemoryParityError                   = 0x08  #  8
    GatewayPathUnavailable              = 0x0A  # 10
    GatewayTargetFailedToRespond        = 0x0B  # 11
