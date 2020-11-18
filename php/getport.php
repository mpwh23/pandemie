<?php

define("DB_HOST", "db5000350590.hosting-data.io");
define("DB_USER", "dbu86934");
define("DB_PASSWORD", "Q&xw+C#52!Frda9g8");
define("DB_DATABASE", "dbs340708");


	$con = mysqli_connect(DB_HOST,DB_USER,DB_PASSWORD,DB_DATABASE);
	$res = mysqli_query($con, "SELECT port FROM python WHERE id = 1");
	
	while ($result = mysqli_fetch_assoc($res)){
		echo $result["port"];
	};
	
	echo $result;
	
	mysqli_close($con);
?>
	