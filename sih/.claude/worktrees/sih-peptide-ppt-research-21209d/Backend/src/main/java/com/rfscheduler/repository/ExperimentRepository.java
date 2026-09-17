package com.rfscheduler.repository;

import com.rfscheduler.domain.ExperimentEntity;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExperimentRepository extends JpaRepository<ExperimentEntity, String> {

    Page<ExperimentEntity> findByStatus(String status, Pageable pageable);
}
