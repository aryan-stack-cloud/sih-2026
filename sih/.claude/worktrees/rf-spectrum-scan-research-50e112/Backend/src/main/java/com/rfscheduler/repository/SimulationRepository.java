package com.rfscheduler.repository;

import com.rfscheduler.domain.SimulationEntity;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SimulationRepository extends JpaRepository<SimulationEntity, String> {

    Page<SimulationEntity> findByStatus(String status, Pageable pageable);

    long countByStatus(String status);
}
