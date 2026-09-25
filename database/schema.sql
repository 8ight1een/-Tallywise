CREATE TABLE users (
      id INT PRIMARY KEY AUTO_INCREMENT,
      email VARCHAR(255) UNIQUE NOT NULL,
      password_hash VARCHAR(250) NOT NULL,
      nickname VARCHAR(100),
      created_at TIMESTAMP DEFAULT current_timestamp
);
CREATE TABLE accounts(
      id INT PRIMARY KEY AUTO_INCREMENT,
      user_id INT NOT NULL,
      name_accounts VARCHAR(100) NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE restrict
 );
CREATE TABLE categories(
      id INT PRIMARY KEY AUTO_INCREMENT,
      user_id INT NOT NULL, 
		name_categories VARCHAR(100) NOT NULL,
		money_type ENUM('收入','支出') NOT NULL,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		
		FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
		UNIQUE KEY (user_id,name_categories)
);
CREATE TABLE transactions(
      id INT PRIMARY KEY AUTO_INCREMENT,
      account_id INT NOT NULL,
      category_id INT NOT NULL,
      user_id INT NOT NULL,
      money DECIMAL(9,2)NOT NULL,
      money_type ENUM('收入','支出') NOT NULL,
      description VARCHAR(250),
      transaction_date DATE NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      
      FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
      FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
      
      INDEX(account_id),
      INDEX(category_id),
      INDEX(user_id),
      INDEX(transaction_date)
);
     

