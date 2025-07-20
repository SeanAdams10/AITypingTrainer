    def summarize_session_ngrams(self) -> int:
        """
        Summarize session ngram performance for all sessions not yet in session_ngram_summary.
        
        Uses complex CTEs to aggregate data from session_ngram_speed, session_ngram_errors,
        and session_keystrokes tables, then inserts the results into session_ngram_summary.
        
        Returns:
            Number of records inserted into session_ngram_summary
            
        Raises:
            DatabaseError: If the database operation fails
        """
        logger.info("Starting SummarizeSessionNgrams process")
        
        # Complex CTE-based query to summarize session ngram data
        query = """
        WITH MissingSessions AS (
            -- Find sessions not yet summarized
            SELECT DISTINCT 
                ps.session_id,
                ps.user_id,
                ps.start_time as updated_dt,
                k.target_ms_per_keystroke as target_speed_ms,
                k.keyboard_id
            FROM practice_sessions ps
            JOIN keyboards k ON ps.keyboard_id = k.keyboard_id
            WHERE ps.session_id NOT IN (
                SELECT DISTINCT session_id 
                FROM session_ngram_summary
            )
        ),
        SessionSpeedSummary AS (
            -- Aggregate speed data for ngrams
            SELECT 
                ms.session_id,
                ms.user_id,
                ms.keyboard_id,
                ms.target_speed_ms,
                ms.updated_dt,
                sns.ngram_text,
                sns.ngram_size,
                AVG(sns.ms_per_keystroke) as avg_ms_per_keystroke,
                COUNT(*) as speed_instance_count
            FROM MissingSessions ms
            INNER JOIN session_ngram_speed sns ON ms.session_id = sns.session_id
            GROUP BY ms.session_id, ms.user_id, ms.keyboard_id, ms.target_speed_ms, ms.updated_dt, sns.ngram_text, sns.ngram_size
        ),
        AddErrors AS (
            -- Add error counts to speed summary
            SELECT 
                sss.session_id,
                sss.user_id,
                sss.keyboard_id,
                sss.target_speed_ms,
                sss.updated_dt,
                sss.ngram_text,
                sss.ngram_size,
                sss.avg_ms_per_keystroke,
                sss.speed_instance_count,
                COALESCE(COUNT(sne.ngram_error_id), 0) as error_count,
                (sss.speed_instance_count + COALESCE(COUNT(sne.ngram_error_id), 0)) as total_instance_count
            FROM SessionSpeedSummary sss
            LEFT OUTER JOIN session_ngram_errors sne ON (
                sss.session_id = sne.session_id 
                AND sss.ngram_text = sne.ngram_text 
                AND sss.ngram_size = sne.ngram_size
            )
            GROUP BY sss.session_id, sss.user_id, sss.keyboard_id, sss.target_speed_ms, sss.updated_dt, 
                     sss.ngram_text, sss.ngram_size, sss.avg_ms_per_keystroke, sss.speed_instance_count
        ),
        AddKeys AS (
            -- Add individual keystroke data as 1-grams
            SELECT 
                ms.session_id,
                ms.user_id,
                ms.keyboard_id,
                ms.target_speed_ms,
                ms.updated_dt,
                sk.expected_char as ngram_text,
                1 as ngram_size,
                AVG(CAST(sk.time_since_previous AS REAL)) as avg_ms_per_keystroke,
                COUNT(*) as instance_count,
                SUM(sk.is_error) as error_count
            FROM MissingSessions ms
            INNER JOIN session_keystrokes sk ON ms.session_id = sk.session_id
            WHERE sk.time_since_previous IS NOT NULL
            GROUP BY ms.session_id, ms.user_id, ms.keyboard_id, ms.target_speed_ms, ms.updated_dt, sk.expected_char
        ),
        AllNgrams AS (
            -- Union speed/error data with keystroke data
            SELECT 
                session_id, user_id, keyboard_id, target_speed_ms, updated_dt,
                ngram_text, ngram_size, avg_ms_per_keystroke, 
                total_instance_count as instance_count, error_count
            FROM AddErrors
            
            UNION ALL
            
            SELECT 
                session_id, user_id, keyboard_id, target_speed_ms, updated_dt,
                ngram_text, ngram_size, avg_ms_per_keystroke, 
                instance_count, error_count
            FROM AddKeys
        ),
        ReadyToInsert AS (
            -- Final preparation for insertion
            SELECT 
                session_id,
                ngram_text,
                user_id,
                keyboard_id,
                ngram_size,
                avg_ms_per_keystroke,
                target_speed_ms,
                instance_count,
                error_count,
                updated_dt
            FROM AllNgrams
            WHERE avg_ms_per_keystroke > 0 AND instance_count > 0
        )
        INSERT INTO session_ngram_summary (
            session_id, ngram_text, user_id, keyboard_id, ngram_size,
            avg_ms_per_keystroke, target_speed_ms, instance_count, error_count, updated_dt
        )
        SELECT 
            session_id, ngram_text, user_id, keyboard_id, ngram_size,
            avg_ms_per_keystroke, target_speed_ms, instance_count, error_count, updated_dt
        FROM ReadyToInsert;
        """
        
        try:
            logger.info("Executing session ngram summary query")
            cursor = self.db.execute(query)
            rows_affected = cursor.rowcount if cursor.rowcount is not None else 0
            
            logger.info(f"Successfully inserted {rows_affected} records into session_ngram_summary")
            
            # Log summary statistics
            summary_stats = self.db.fetchone(
                "SELECT COUNT(*) as total_records, COUNT(DISTINCT session_id) as unique_sessions FROM session_ngram_summary"
            )
            
            if summary_stats:
                logger.info(f"Total records in session_ngram_summary: {summary_stats['total_records']}")
                logger.info(f"Unique sessions in session_ngram_summary: {summary_stats['unique_sessions']}")
            
            return rows_affected
            
        except Exception as e:
            logger.error(f"Error in SummarizeSessionNgrams: {str(e)}")
            raise
