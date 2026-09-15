/*
 * Copyright (c) 2023 - 2026 Chair for Design Automation, TUM
 * Copyright (c) 2025 - 2026 Munich Quantum Software Company GmbH
 * All rights reserved.
 *
 * SPDX-License-Identifier: MIT
 *
 * Licensed under the MIT License
 */

#pragma once

#include "na/zoned/Types.hpp"

#include <stdexcept>
#include <unordered_set>
#include <vector>

namespace na::zoned {
/**
 * Thrown by a placer when a placement search fails because the search space
 * was artificially restricted by a (too narrow) search window rather than
 * because no valid placement exists at all. This is distinguishable from
 * other placement failures so that callers (or the placer itself) can retry
 * with a wider window before giving up.
 */
class WindowTooSmallError : public std::runtime_error {
public:
  using std::runtime_error::runtime_error;
};

/**
 * The Abstract Base Class for the Placer of the MQT's Zoned Neutral Atom
 * Compiler.
 */
class PlacerBase {
public:
  virtual ~PlacerBase() = default;

  /**
   * This function defines the interface of the placer.
   * @param nQubits denotes the number of qubits to be placed
   * @param twoQubitGateLayers are the qubits that must be placed for each layer
   * @param reuseQubits are the qubits that are reused in the next stage
   * @param initialPlacement optionally seeds the starting site of some
   * qubits' atoms, e.g., to resume from where a previous, separate compile()
   * call on the same physical atoms left off. Qubits not present in it are
   * placed freely.
   */
  [[nodiscard]] virtual auto
  place(size_t nQubits,
        const std::vector<TwoQubitGateLayer>& twoQubitGateLayers,
        const std::vector<std::unordered_set<qc::Qubit>>& reuseQubits,
        const InitialPlacement& initialPlacement = {})
      -> std::vector<Placement> = 0;
};
} // namespace na::zoned
