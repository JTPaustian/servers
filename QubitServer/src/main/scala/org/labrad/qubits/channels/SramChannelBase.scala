package org.labrad.qubits.channels

import org.labrad.qubits.Experiment
import org.labrad.qubits.FpgaModelDac
import org.labrad.qubits.resources.DacBoard
import scala.collection.mutable

abstract class SramChannelBase[T](val name: String) extends SramChannel {

  private var expt: Experiment = null
  private var board: DacBoard = null
  protected var fpga: FpgaModelDac = null

  override def getExperiment(): Experiment = {
    expt
  }

  override def setExperiment(expt: Experiment): Unit = {
    this.expt = expt
  }

  override def getDacBoard(): DacBoard = {
    board
  }

  def setDacBoard(board: DacBoard): Unit = {
    this.board = board
  }

  override def getFpgaModel(): FpgaModelDac = {
    fpga
  }


  //
  // Blocks
  //
  protected var currentBlock: String = null
  def getCurrentBlock(): String = {
    currentBlock
  }
  def setCurrentBlock(block: String): Unit = {
    currentBlock = block
  }

  protected val blocks = mutable.Map.empty[String, T]

  // Start delay
  override def getStartDelay(): Int = {
    this.getFpgaModel().getStartDelay()
  }

  override def setStartDelay(startDelay: Int): Unit = {
    this.getFpgaModel().setStartDelay(startDelay)
  }
}
